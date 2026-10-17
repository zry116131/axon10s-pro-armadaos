// SPDX-License-Identifier: GPL-2.0-only
/*
 *  Driver for Synaptics TCM Oncell Touchscreens
 *
 *  Copyright (c) 2024 Frieder Hannenheim <frieder.hannenheim@proton.me>
 *  Copyright (c) 2024 Caleb Connolly <caleb@postmarketos.org>
 */

#include <linux/unaligned.h>
#include <linux/gpio/consumer.h>
#include <linux/completion.h>
#include <linux/mutex.h>
#include "tcm_report.h"
#include <linux/i2c.h>
#include <linux/input.h>
#include <linux/input/touchscreen.h>
#include <linux/mod_devicetable.h>
#include <linux/module.h>
#include <linux/property.h>
#include <linux/delay.h>
#include <linux/input/mt.h>
#include <linux/input/touchscreen.h>
#include <linux/interrupt.h>
#include <linux/irq.h>
#include <linux/module.h>
#include <linux/pm_runtime.h>
#include <linux/regulator/consumer.h>

/*
 * The TCM oncell interface uses a command byte, which may be followed by additional
 * data. The packet format is defined in the tcm_cmd struct.
 *
 * The following list only defines commands that are used in this driver (and their
 * counterparts for context). Vendor reference implementations can be found at
 * https://github.com/LineageOS/android_kernel_oneplus_sm8250/tree/ee0a7ee1939ffd53000e42051caf8f0800defb27/drivers/input/touchscreen/synaptics_tcm
 */

/*
 * Request information about the chip. We don't send this command explicitly as
 * the controller automatically sends this information when starting up.
 */
#define TCM_IDENTIFY				0x02

/* Enable/disable reporting touch inputs */
#define TCM_ENABLE_REPORT			0x05
#define TCM_DISABLE_REPORT			0x06

/*
 * After powering on, we send this to exit the bootloader mode and run the main
 * firmware.
 */
#define TCM_RUN_APPLICATION_FIRMWARE		0x14

/*
 * Reports information about the vendor provided application firmware. This is
 * also used to determine when the firmware has finished booting.
 */
#define TCM_GET_APPLICATION_INFO		0x20

#define MODE_APPLICATION			0x01

#define APP_STATUS_OK				0x00
#define APP_STATUS_BOOTING			0x01
#define APP_STATUS_UPDATING			0x02

/* status codes */
#define REPORT_IDLE				0x00
#define REPORT_OK				0x01
#define REPORT_BUSY				0x02
#define REPORT_CONTINUED_READ			0x03
#define REPORT_RECEIVE_BUFFER_OVERFLOW		0x0c
#define REPORT_PREVIOUS_COMMAND_PENDING		0x0d
#define REPORT_NOT_IMPLEMENTED			0x0e
#define REPORT_ERROR				0x0f

/* report types */
#define REPORT_IDENTIFY				0x10
#define REPORT_TOUCH				0x11
#define REPORT_DELTA				0x12
#define REPORT_RAW				0x13
#define REPORT_DEBUG				0x14
#define REPORT_LOG				0x1d
#define REPORT_TOUCH_HOLD			0x20
#define REPORT_INVALID				0xff

struct tcm_message_header {
	u8 marker;
	u8 code;
	__le16 length;
} __packed;

struct tcm_cmd {
	u8 cmd;
	__le16 length;
	u8 data[];
};

struct tcm_identification {
	struct tcm_message_header header;
	u8 version;
	u8 mode;
	char part_number[16];
	u8 build_id[4];
	u8 max_write_size[2];
} __packed;

struct tcm_app_info {
	struct tcm_message_header header;
	u8 version[2];
	__le16 status;
	u8 static_config_size[2];
	u8 dynamic_config_size[2];
	u8 app_config_start_write_block[2];
	u8 app_config_size[2];
	u8 max_touch_report_config_size[2];
	u8 max_touch_report_payload_size[2];
	char customer_config_id[16];
	__le16 max_x;
	__le16 max_y;
	u8 max_objects[2];
	u8 num_of_buttons[2];
	u8 num_of_image_rows[2];
	u8 num_of_image_cols[2];
	u8 has_hybrid_data[2];
} __packed;

struct tcm_data {
	struct i2c_client *client;
	struct mutex command_lock;
	u8 expected;
	bool ready;
	bool contact_seen;
	u8 report_config[128];
	u16 report_config_len;
	struct input_dev *input;
	struct gpio_desc *reset_gpio;
	struct completion response;
	struct touchscreen_properties props;
	struct regulator_bulk_data supplies[2];

	/* annoying state */
	u16 buf_size;
	char buf[260];
};

static int tcm_recv_report(struct tcm_data *tcm,
			   void *buf, size_t length)
{
	struct i2c_client *client = tcm->client;
	struct i2c_msg msg;
	int ret;

	msg.addr = client->addr;
	msg.flags = I2C_M_RD;
	msg.len = length;
	msg.buf = buf;

	ret = i2c_transfer(client->adapter, &msg, 1);
	if (ret == 1)
		return 0;
	else if (ret < 0)
		return ret;
	else
		return -EIO;
}

static int tcm_command(struct tcm_data *tcm, u8 cmd, int arg, void *buf, size_t length)
{
    u8 packet[4] = {cmd, arg < 0 ? 0 : 1, 0, arg};
    int ret, n = arg < 0 ? 3 : 4;
    mutex_lock(&tcm->command_lock);
    reinit_completion(&tcm->response);
    WRITE_ONCE(tcm->expected, cmd == TCM_RUN_APPLICATION_FIRMWARE ? REPORT_IDENTIFY : REPORT_OK);
    ret=i2c_master_send(tcm->client, packet, n);
    if(ret!=n) { ret=ret<0?ret:-EIO; goto out; }
    if(!wait_for_completion_timeout(&tcm->response,msecs_to_jiffies(1000))) {
        ret=-ETIMEDOUT; goto out;
    }
    if(tcm->buf[1]!=READ_ONCE(tcm->expected)) { ret=-EIO; goto out; }
    if(buf) {
        if(length>tcm->buf_size) { ret=-EMSGSIZE; goto out; }
        memcpy(buf,tcm->buf,length);
    }
    ret=0;
out:
    WRITE_ONCE(tcm->expected,0);
    mutex_unlock(&tcm->command_lock);
    return ret;
}
static int tcm_read_message(struct tcm_data *tcm, u8 cmd, void *buf, size_t length)
{
    return tcm_command(tcm,cmd,-1,buf,length);
}
static void tcm_power_off(void *data)
{
    struct tcm_data *tcm=data;
    gpiod_set_value_cansleep(tcm->reset_gpio,1);
    regulator_bulk_disable(ARRAY_SIZE(tcm->supplies),tcm->supplies);
}
static int tcm_input_open(struct input_dev *dev)
{
    return tcm_command(input_get_drvdata(dev),TCM_ENABLE_REPORT,REPORT_TOUCH,NULL,0);
}
static void tcm_input_close(struct input_dev *dev)
{
    tcm_command(input_get_drvdata(dev),TCM_DISABLE_REPORT,REPORT_TOUCH,NULL,0);
}

static int tcm_handle_touch_report(struct tcm_data *tcm, const char *buf, size_t len)
{
    struct tcm_contact contacts[10];
    unsigned int i, contacts_used=0;
    if(!READ_ONCE(tcm->ready) || len<4) return 0;
    if(tcm_parse(tcm->report_config,tcm->report_config_len,(const u8 *)buf+4,len-4,contacts)) {
        dev_warn_ratelimited(&tcm->client->dev,"TCM invalid touch report len=%zu\n",len);
        return -EINVAL;
    }
    for(i=0;i<10;i++) {
        struct tcm_contact *c=&contacts[i];
        if(c->status!=1 && c->status!=2) continue;
        if(c->x>tcm->props.max_x || c->y>tcm->props.max_y) continue;
        contacts_used++;
        input_mt_slot(tcm->input,i);
        input_mt_report_slot_state(tcm->input,MT_TOOL_FINGER,true);
        touchscreen_report_pos(tcm->input,&tcm->props,c->x,c->y,true);
        input_report_abs(tcm->input,ABS_MT_PRESSURE,min(c->z,255U));
        input_report_abs(tcm->input,ABS_MT_TOUCH_MAJOR,min(max(c->wx,c->wy),255U));
        input_report_abs(tcm->input,ABS_MT_TOUCH_MINOR,min(min(c->wx,c->wy),255U));
    }
    if(contacts_used && !tcm->contact_seen) {
        tcm->contact_seen=true;
        dev_info(&tcm->client->dev,"AXON_TCM_FIRST_CONTACT_FRAME_ACCEPTED\n");
    }
    input_mt_sync_frame(tcm->input);
    input_sync(tcm->input);
    return 0;
}

static irqreturn_t tcm_report_irq(int irq, void *data)
{
	struct tcm_data *tcm = data;
	struct tcm_message_header *header;
	char buf[260];
	u16 len;
	int ret;

	header = (struct tcm_message_header *)buf;
	ret = tcm_recv_report(tcm, buf, sizeof(buf));
	if (ret) {
		dev_err(&tcm->client->dev, "failed to read report: %d\n", ret);
		return IRQ_HANDLED;
	}

	switch (header->code) {
	case REPORT_ERROR:
	case REPORT_NOT_IMPLEMENTED:
	case REPORT_OK:
	case REPORT_IDENTIFY:
	case REPORT_TOUCH:
	case REPORT_DELTA:
	case REPORT_RAW:
	case REPORT_DEBUG:
	case REPORT_TOUCH_HOLD:
		break;
	default:
		dev_dbg(&tcm->client->dev, "Ignoring report %#x\n", header->code);
		return IRQ_HANDLED;
	}

	if (header->marker != 0xa5) return IRQ_HANDLED;
	len = le16_to_cpu(header->length);

	dev_dbg(&tcm->client->dev, "report %#x len %u\n", header->code, len);

	if (len > sizeof(buf) - sizeof(*header)) {
		dev_err(&tcm->client->dev, "report too long\n");
		return IRQ_HANDLED;
	}

	/* Check if this is a read response or an indication. For indications
	 * (user touched the screen) we just parse the report directly.
	 */
	if (header->code == REPORT_TOUCH) {
		tcm_handle_touch_report(tcm, buf, len + sizeof(*header));
		return IRQ_HANDLED;
	}

	if (completion_done(&tcm->response) || !READ_ONCE(tcm->expected) || (header->code != READ_ONCE(tcm->expected) && header->code != REPORT_ERROR && header->code != REPORT_NOT_IMPLEMENTED))
		return IRQ_HANDLED;
	tcm->buf_size = len + sizeof(*header);
	memcpy(tcm->buf, buf, len + sizeof(*header));
	complete(&tcm->response);

	return IRQ_HANDLED;
}

static int tcm_hw_init(struct tcm_data *tcm, u16 *max_x, u16 *max_y)
{
	int ret;
	struct tcm_identification id = { 0 };
	struct tcm_app_info app_info = { 0 };
	u16 status;
	unsigned int tries=0;
	u8 config[132];

	/*
	 * Tell the firmware to start up. After starting it sends an IDENTIFY report, which
	 * we treat like a response to this message even though it's technically a new report.
	 */
	/* Consume the reset IDENTIFY report without issuing a second IDENTIFY. */
    if (!wait_for_completion_timeout(&tcm->response, msecs_to_jiffies(1000)))
        ret = -ETIMEDOUT;
    else if (tcm->buf[1] != REPORT_IDENTIFY || tcm->buf_size < sizeof(id))
        ret = -EMSGSIZE;
    else { memcpy(&id, tcm->buf, sizeof(id)); ret = 0; }
    WRITE_ONCE(tcm->expected, 0);
	if (ret) {
		dev_err(&tcm->client->dev, "failed to identify device: %d\n", ret);
		return ret;
	}

	dev_info(&tcm->client->dev, "Synaptics TCM %.16s v%d mode %d\n",
		id.part_number, id.version, id.mode);
	if (id.mode != MODE_APPLICATION) {
		/* We don't support firmware updates or anything else */
		dev_err(&tcm->client->dev, "Device is not in application mode\n");
		return -ENODEV;
	}

	do {
		msleep(20);
		ret = tcm_read_message(tcm, TCM_GET_APPLICATION_INFO, &app_info, sizeof(app_info));
		if (ret) {
			dev_err(&tcm->client->dev, "failed to get application info: %d\n", ret);
			return ret;
		}
		status = le16_to_cpu(app_info.status);
	} while (++tries < 25 && (status == APP_STATUS_BOOTING || status == APP_STATUS_UPDATING));
	if (status != APP_STATUS_OK) return -ETIMEDOUT;

	dev_dbg(&tcm->client->dev, "Application firmware v%d.%d (customer '%.16s') status %d\n",
		 app_info.version[0], app_info.version[1], app_info.customer_config_id,
		 status);

	*max_x = le16_to_cpu(app_info.max_x);
	*max_y = le16_to_cpu(app_info.max_y);

    if (*max_x != 1079 || *max_y != 2339 || get_unaligned_le16(app_info.max_objects) != 10)
        return -ENODEV;
    ret=tcm_read_message(tcm,0x25,config,sizeof(config));
    if(ret) return ret;
    memcpy(tcm->report_config,config+4,128);
    tcm->report_config_len=128;
    dev_info(&tcm->client->dev,"AXON_TCM_READY max=%ux%u config=%*ph\n",*max_x,*max_y,32,tcm->report_config);
    return 0;
}

static int tcm_power_on(struct tcm_data *tcm)
{
	int ret;

	ret = regulator_bulk_enable(ARRAY_SIZE(tcm->supplies),
				    tcm->supplies);
	if (ret)
		return ret;

	msleep(200);
	gpiod_set_value_cansleep(tcm->reset_gpio, 1);
	usleep_range(2000, 3000);
	gpiod_set_value_cansleep(tcm->reset_gpio, 0);
	msleep(100);

	return 0;
}

static int tcm_probe(struct i2c_client *client)
{
	struct tcm_data *tcm;
	u16 max_x, max_y;
	int ret;

	if (!i2c_check_functionality(client->adapter, I2C_FUNC_I2C))
		return -ENODEV;

	tcm = devm_kzalloc(&client->dev, sizeof(struct tcm_data), GFP_KERNEL);
	if (!tcm)
		return -ENOMEM;

	i2c_set_clientdata(client, tcm);
	tcm->client = client;

	init_completion(&tcm->response);
	mutex_init(&tcm->command_lock);
    WRITE_ONCE(tcm->expected, REPORT_IDENTIFY);

	tcm->supplies[0].supply = "vdd";
	tcm->supplies[1].supply = "vcc";
	ret = devm_regulator_bulk_get(&client->dev, ARRAY_SIZE(tcm->supplies),
				      tcm->supplies);
	if (ret)
		return ret;

    tcm->reset_gpio=devm_gpiod_get(&client->dev,"reset",GPIOD_OUT_HIGH);
    if(IS_ERR(tcm->reset_gpio)) return PTR_ERR(tcm->reset_gpio);
    ret=tcm_power_on(tcm);
    if(ret) return ret;
    ret=devm_add_action_or_reset(&client->dev,tcm_power_off,tcm);
    if(ret) return ret;

	ret = devm_request_threaded_irq(&client->dev, client->irq, NULL,
					tcm_report_irq,
					IRQF_ONESHOT,
					"synaptics_tcm_report", tcm);
	if (ret < 0)
		return ret;

	ret = tcm_hw_init(tcm, &max_x, &max_y);
	if (ret) {
		dev_err(&client->dev, "failed to initialize hardware\n");
		return ret;
	}

	tcm->input = devm_input_allocate_device(&client->dev);
	if (!tcm->input)
		return -ENOMEM;

	tcm->input->name = "Synaptics TCM Oncell Touchscreen";
	tcm->input->id.bustype = BUS_I2C;
	tcm->input->open = tcm_input_open;
	tcm->input->close = tcm_input_close;

	input_set_abs_params(tcm->input, ABS_MT_POSITION_X, 0, max_x, 0, 0);
	input_set_abs_params(tcm->input, ABS_MT_POSITION_Y, 0, max_y, 0, 0);
	input_set_abs_params(tcm->input, ABS_MT_TOUCH_MAJOR, 0, 255, 0, 0);
	input_set_abs_params(tcm->input, ABS_MT_TOUCH_MINOR, 0, 255, 0, 0);
	input_set_abs_params(tcm->input, ABS_MT_PRESSURE, 0, 255, 0, 0);

	touchscreen_parse_properties(tcm->input, true, &tcm->props);

	ret = input_mt_init_slots(tcm->input, 10, INPUT_MT_DIRECT | INPUT_MT_DROP_UNUSED);
	if (ret)
		return ret;

	input_set_drvdata(tcm->input, tcm);

	ret = input_register_device(tcm->input);
	if (ret)
		return ret;

	WRITE_ONCE(tcm->ready,true);
	return 0;
}

static const struct of_device_id syna_driver_ids[] = {
	{
		.compatible = "syna,s3908",
	},
	{}
};
MODULE_DEVICE_TABLE(of, syna_driver_ids);

static const struct i2c_device_id syna_i2c_ids[] = {
	{ "axon-tcm-repair93", 0 },
	{ }
};

MODULE_DEVICE_TABLE(i2c, syna_i2c_ids);

static struct i2c_driver syna_i2c_driver = {
	.probe		= tcm_probe,
	.id_table	= syna_i2c_ids,
	.driver		= {
	.name		= "axon-tcm-repair93",
	.of_match_table	= syna_driver_ids,
	},
};

module_i2c_driver(syna_i2c_driver);

MODULE_LICENSE("GPL");
MODULE_AUTHOR("Frieder Hannenheim <frieder.hannenheim@proton.me>");
MODULE_AUTHOR("Caleb Connolly <caleb@postmarketos.org>");
MODULE_DESCRIPTION("A driver for Synaptics TCM Oncell Touchpanels");


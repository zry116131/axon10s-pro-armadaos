/*
 * Synaptics TCM touchscreen driver
 *
 * Copyright (C) 2017-2019 Synaptics Incorporated. All rights reserved.
 *
 * Copyright (C) 2017-2019 Scott Lin <scott.lin@tw.synaptics.com>
 *
 * This program is free software; you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation; either version 2 of the License, or
 * (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
 * GNU General Public License for more details.
 *
 * INFORMATION CONTAINED IN THIS DOCUMENT IS PROVIDED "AS-IS," AND SYNAPTICS
 * EXPRESSLY DISCLAIMS ALL EXPRESS AND IMPLIED WARRANTIES, INCLUDING ANY
 * IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE,
 * AND ANY WARRANTIES OF NON-INFRINGEMENT OF ANY INTELLECTUAL PROPERTY RIGHTS.
 * IN NO EVENT SHALL SYNAPTICS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
 * SPECIAL, PUNITIVE, OR CONSEQUENTIAL DAMAGES ARISING OUT OF OR IN CONNECTION
 * WITH THE USE OF THE INFORMATION CONTAINED IN THIS DOCUMENT, HOWEVER CAUSED
 * AND BASED ON ANY THEORY OF LIABILITY, WHETHER IN AN ACTION OF CONTRACT,
 * NEGLIGENCE OR OTHER TORTIOUS ACTION, AND EVEN IF SYNAPTICS WAS ADVISED OF
 * THE POSSIBILITY OF SUCH DAMAGE. IF A TRIBUNAL OF COMPETENT JURISDICTION DOES
 * NOT PERMIT THE DISCLAIMER OF DIRECT DAMAGES OR ANY OTHER DAMAGES, SYNAPTICS'
 * TOTAL CUMULATIVE LIABILITY TO ANY PARTY SHALL NOT EXCEED ONE HUNDRED U.S.
 * DOLLARS.
 */

/* SPDX-License-Identifier: GPL-2.0-only
 * Bounded adaptation of Synaptics touch_parse_report()/touch_get_report_data().
 * Protocol definitions: LineageOS ee0a7ee1939ffd53000e42051caf8f0800defb27,
 * drivers/input/touchscreen/synaptics_tcm/synaptics_tcm_touch.c.
 * Read the controller's report configuration; never replace its configuration.
 */
struct tcm_contact { unsigned int status, x, y, z, wx, wy; };
static int tcm_parse(const unsigned char *cfg, unsigned int cn,
                     const unsigned char *p, unsigned int pn,
                     struct tcm_contact out[10])
{
    unsigned int pc=0, off=0, obj=0, loop=0, startbit=0, rounds=0;
    unsigned int count=0, steps=0, code, bits, value, j;
    int active=0, counted=0, inloop=0;
    for (j=0;j<10;j++) out[j]=(struct tcm_contact){0};
    while (pc<cn && ++steps<=2048) {
        code=cfg[pc++];
        switch (code) {
        case 0: return 0;
        case 1: case 2:
            if (inloop) return -1;
            active=code==1; loop=pc; startbit=off; obj=0; rounds=0; inloop=1;
            if (active && ((counted && !count) || off==pn*8)) {
                while (pc<cn && cfg[pc]!=3) {
                    if (cfg[pc]==0 || cfg[pc]==1 || cfg[pc]==2) return -1;
                    pc += cfg[pc]==4 ? 1 : 2;
                }
                if (pc>=cn) return -1;
                pc++; inloop=0;
            }
            break;
        case 3:
            if (!inloop || off<=startbit) return -1;
            rounds++;
            if (rounds<10 && (active ? (counted ? rounds<count : pn*8-off>=8) : rounds<10)) {
                pc=loop; startbit=off; if (!active) obj=rounds;
            } else inloop=0;
            break;
        case 4:
            off=(off+7)&~7U;
            if (off>pn*8) return -1;
            break;
        default:
            if (pc>=cn) return -1;
            bits=cfg[pc++];
            if (!bits || off>pn*8 || bits>pn*8-off) return -1;
            /* Firmware may report wide gesture/diagnostic fields. Consume
             * those without interpreting them as a coordinate scalar. */
            if (!(code>=6 && code<=12) && code!=24) { off+=bits; break; }
            if (bits>32) return -1;
            value=0;
            for (j=0;j<bits;j++) value |= ((p[(off+j)/8]>>((off+j)%8))&1U)<<j;
            off+=bits;
            if (code==6) { if(value>=10) return -1; obj=value; }
            else if (code>=7 && code<=12) {
                if(obj>=10) return -1;
                switch(code) {
                case 7: out[obj].status=value; break;
                case 8: out[obj].x=value; break;
                case 9: out[obj].y=value; break;
                case 10: out[obj].z=value; break;
                case 11: out[obj].wx=value; break;
                case 12: out[obj].wy=value; break;
                }
            } else if(code==24) { if(value>10) return -1; count=value; counted=1; }
            break;
        }
    }
    return -1;
}

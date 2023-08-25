import asyncio
import iterm2
import re

async def main(connection):
    component = iterm2.StatusBarComponent(
            short_description='Battery Charge',
            detailed_description='This plugin displays the current battery charge.(requires iStats ruby gem)',
            exemplar='󰂂 90%',
            update_cadence=5,
            identifier='vxider.iterm-components.battery_charge',
            knobs=[],
            )

    @iterm2.StatusBarRPC
    async def battery_charge_coroutine(knobs):
        proc = await asyncio.create_subprocess_shell(
                "/usr/bin/pmset -g batt",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                )
        stdout, stderr = await proc.communicate()
        status = stdout.decode().strip();
        icon = None
        estimate = None
        percentage = None
        if ("charged" in status):
            icon='󰂅 %100'
            return f'{icon}' if not stderr else '󰁹 N/A'
        else:
            percentage = re.search('[0-9]*%', status).group(0)[:-1]
            if ("no estimate" in status):
                estimate = 'no estimate'
            else:
                estimate = re.search('[0-9]+:[0-9]+', status).group(0)

            charge_icons=None
            if ("discharging" in status):
                charge_icons="󰂎 󰁺 󰁻 󰁼 󰁽 󰁾 󰁿 󰂀 󰂁 󰂂 󰁹 "
            else:
                charge_icons="󰢟 󰢜 󰂆 󰂇 󰂈 󰢝 󰂉 󰢞 󰂊 󰂋 󰂅 "
            if percentage == "100":
                icon = "󰁹%100"
            else:
                icon=charge_icons.split()[ord(percentage[0]) - 48]
            return f'{icon} {percentage}% {estimate}' if not stderr else '󰁹 N/A'

    await component.async_register(connection, battery_charge_coroutine)

iterm2.run_forever(main)

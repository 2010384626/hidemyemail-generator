import asyncio
import datetime
import os
from typing import Union, List, Optional
import re

from rich.text import Text
from rich.console import Console
from rich.table import Table

from icloud import HideMyEmail

MAX_CONCURRENT_TASKS = 10

class RichHideMyEmail(HideMyEmail):
    def __init__(self, cookie_string: str):
        super().__init__(cookies=cookie_string)
        self.console = Console()
        self.table = Table()

    async def _generate_one(self) -> Union[str, None]:
        # First, generate an email
        gen_res = await self.generate_email()

        if not gen_res:
            return
        elif "success" not in gen_res or not gen_res["success"]:
            error = gen_res.get("error", {})
            err_msg = "Unknown"
            if isinstance(error, int) and "reason" in gen_res:
                err_msg = gen_res["reason"]
            elif isinstance(error, dict) and "errorMessage" in error:
                err_msg = error["errorMessage"]
            self.console.log(
                f"[bold red][ERR][/] - Failed to generate email. Reason: {err_msg}"
            )
            return

        email = gen_res["result"]["hme"]
        self.console.log(f'[50%] "{email}" - Successfully generated')

        # Then, reserve it
        reserve_res = await self.reserve_email(email)

        if not reserve_res:
            return
        elif "success" not in reserve_res or not reserve_res["success"]:
            error = reserve_res.get("error", {})
            err_msg = "Unknown"
            if isinstance(error, int) and "reason" in reserve_res:
                err_msg = reserve_res["reason"]
            elif isinstance(error, dict) and "errorMessage" in error:
                err_msg = error["errorMessage"]
            self.console.log(
                f'[bold red][ERR][/] "{email}" - Failed to reserve email. Reason: {err_msg}'
            )
            return

        self.console.log(f'[100%] "{email}" - Successfully reserved')
        return email

    async def _generate(self, num: int):
        tasks = []
        for _ in range(num):
            task = asyncio.ensure_future(self._generate_one())
            tasks.append(task)

        return filter(lambda e: e is not None, await asyncio.gather(*tasks))

    async def generate(self, count: int) -> List[str]:
        emails = []
        self.console.rule()
        self.console.log(f"Generating {count} email(s) for current cookie...")
        self.console.rule()

        with self.console.status(f"[bold green]Generating iCloud email(s)..."):
            while count > 0:
                batch = await self._generate(
                    count if count < MAX_CONCURRENT_TASKS else MAX_CONCURRENT_TASKS
                )
                count -= MAX_CONCURRENT_TASKS
                emails += batch

        if len(emails) > 0:
            with open("emails.txt", "a+") as f:
                f.write(os.linesep.join(emails) + os.linesep)

            self.console.rule()
            self.console.log(
                f':star: Emails have been saved into the "emails.txt" file'
            )

            self.console.log(
                f"[bold green]All done![/] Successfully generated [bold green]{len(emails)}[/] email(s)"
            )

        return list(emails)

    async def list(self, active: bool, search: str) -> None:
        gen_res = await self.list_email()
        if not gen_res:
            return

        if "success" not in gen_res or not gen_res["success"]:
            error = gen_res.get("error", {})
            err_msg = "Unknown"
            if isinstance(error, int) and "reason" in gen_res:
                err_msg = gen_res["reason"]
            elif isinstance(error, dict) and "errorMessage" in error:
                err_msg = error["errorMessage"]
            self.console.log(
                f"[bold red][ERR][/] - Failed to list email. Reason: {err_msg}"
            )
            return

        self.table.add_column("Label")
        self.table.add_column("Hide my email")
        self.table.add_column("Created Date Time")
        self.table.add_column("IsActive")

        for row in gen_res["result"]["hmeEmails"]:
            if row["isActive"] == active:
                if search is not None and re.search(search, row["label"]):
                    self.table.add_row(
                        row["label"],
                        row["hme"],
                        str(
                            datetime.datetime.fromtimestamp(
                                row["createTimestamp"] / 1000
                            )
                        ),
                        str(row["isActive"]),
                    )
                else:
                    self.table.add_row(
                        row["label"],
                        row["hme"],
                        str(
                            datetime.datetime.fromtimestamp(
                                row["createTimestamp"] / 1000
                            )
                        ),
                        str(row["isActive"]),
                    )

        self.console.print(self.table)


async def generate(count: Optional[int]) -> None:
    # 强制将默认生成的数量修改为 10
    if count is None:
        count = 10
        
    cookie_file = "cookie.txt"
    console = Console()
    
    if not os.path.exists(cookie_file):
        console.log('[bold yellow][WARN][/] No "cookie.txt" file found! Generation might not work due to unauthorized access.')
        return

    # 读取 cookie.txt 里的所有非注释行，支持同时放入多个 Cookie
    with open(cookie_file, "r") as f:
        cookies = [line.strip() for line in f if not line.startswith("//") and line.strip()]

    if not cookies:
        console.log('[bold red][ERR][/] No valid cookies found in "cookie.txt"!')
        return

    for i, cookie in enumerate(cookies, 1):
        console.log(f"[bold blue]Processing cookie {i}/{len(cookies)}...[/]")
        async with RichHideMyEmail(cookie_string=cookie) as hme:
            await hme.generate(count)


async def list_emails(active: bool, search: str) -> None:
    cookie_file = "cookie.txt"
    console = Console()
    if not os.path.exists(cookie_file):
        console.log('[bold yellow][WARN][/] No "cookie.txt" file found!')
        return
        
    with open(cookie_file, "r") as f:
        cookies = [line.strip() for line in f if not line.startswith("//") and line.strip()]

    if not cookies:
        console.log('[bold red][ERR][/] No valid cookies found!')
        return
        
    # 查询列表仅使用第一个 Cookie
    async with RichHideMyEmail(cookie_string=cookies[0]) as hme:
        await hme.list(active, search)


if __name__ == "__main__":
    loop = asyncio.new_event_loop()
    try:
        loop.run_until_complete(generate(None))
    except KeyboardInterrupt:
        pass

import datetime
import functools
import os
import shutil
import sys
from pathlib import Path
from typing import Any, List

import aiosqlite
from rich import print

INTERNAL_VERSION_TABLE_NAME = "__version_table__"


def reduce_by_empty_newline(a: List[List[Any]], x) -> List[List[Any]]:
    a[-1].append(x)
    if len(x) == 1 and x == "\n":
        a.append([])
    return a


class Database:
    db_path: str
    schema_path: str

    def __init__(self, db_path: str):
        self.db_path = Path(db_path).resolve()
        self.schema_path = Path(__file__).resolve().parent / "schema"

    async def _initialize_schemas(self, schema_dirents: List[os.DirEntry]):
        new_ver = None
        async with aiosqlite.connect(self.db_path) as db:
            for dirent in schema_dirents:
                try:
                    with open(dirent.path, "r") as scf:
                        lines = scf.readlines()
                        exec_lists = functools.reduce(
                            reduce_by_empty_newline, lines, [[]]
                        )
                        for exec_list in exec_lists:
                            exec_str = "".join(exec_list)
                            await db.execute(exec_str)
                        await db.commit()
                        print(f"{len(exec_lists)} statements in {dirent.name}")

                        new_ver = schema_dirents[-1].name.strip(".sql")
                        now = datetime.datetime.now()
                        await db.execute(
                            "insert into "
                            + INTERNAL_VERSION_TABLE_NAME
                            + " values (?, ?, ?)",
                            (new_ver, now, now),
                        )
                        await db.commit()
                except:
                    raise Exception(f"_initialize_schemas at {dirent}")
            return new_ver

    async def initialize(self):
        schema_dirents: List[os.DirEntry] = list(
            filter(
                lambda o: o.name.endswith(".sql"),
                sorted(
                    os.scandir(path=self.schema_path),
                    key=lambda o: o.name,
                ),
            )
        )

        if not os.path.exists(self.db_path):
            print(f"Creating database...")
            try:
                async with aiosqlite.connect(self.db_path) as db:
                    await db.execute(
                        """create table """
                        + INTERNAL_VERSION_TABLE_NAME
                        + """(version text not null,
                            created date not null,
                            updated date not null
                        )"""
                    )
                    await db.commit()

                new_ver = await self._initialize_schemas(schema_dirents)
                print(f"Created database v{new_ver} at {self.db_path}")
            except:
                print(f"DB init failed", exc_info=True)
                os.remove(self.db_path)
                sys.exit(-1)
        else:
            ver_rows = await self._direct_exec(
                f"select version from {INTERNAL_VERSION_TABLE_NAME}"
            )

            if len(ver_rows) > len(schema_dirents):
                raise Exception(
                    f"DB is newer than schema! {ver_rows} vs {schema_dirents}"
                )

            if len(ver_rows) == len(schema_dirents):
                if ver_rows[-1][0] != schema_dirents[-1].name.strip(".sql"):
                    raise Exception(
                        f"DB version mismatch! {ver_rows[-1][0]} vs. {schema_dirents[-1].name}"
                    )
                print(f"Initialized DB at version {ver_rows[-1][0]}")
                return

            cur_ver = ver_rows[-1][0]
            shutil.copyfile(self.db_path, f"{self.db_path}__v{cur_ver}.backup")
            num_vers_to_update = len(schema_dirents) - len(ver_rows)
            update_schemas = schema_dirents[-num_vers_to_update:]
            new_ver = await self._initialize_schemas(update_schemas)
            print(
                f"Updated DB to v{new_ver} with {len(update_schemas)} additional schemas: {', '.join([i.name for i in update_schemas])}"
            )

    async def _direct_exec(self, sql, p_tuple=()):
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(sql, p_tuple)
            await db.commit()
            return await cursor.fetchall()


class SSHPokerDB(Database):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    async def get_user(self, pubkey_b64: str):
        res = await self._direct_exec(
            "select * from user where pubkey = ?", (pubkey_b64,)
        )

        if len(res) == 0:
            return None

        return res[0]

    async def new_user(self, pubkey_b64: str, username: str):
        return await self._direct_exec(
            "insert into user values (?, ?, ?)",
            (pubkey_b64, username, datetime.datetime.now()),
        )

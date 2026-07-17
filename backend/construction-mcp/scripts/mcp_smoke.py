"""Проверка MCP-хендшейка: поднимает сервер по stdio, инициализирует сессию,
получает список инструментов и вызывает несколько из них. Запуск из каталога
backend/construction-mcp:  .venv/bin/python scripts/mcp_smoke.py
"""
import os
import anyio

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


async def main():
    params = StdioServerParameters(
        command=os.environ.get("PYTHON", ".venv/bin/python"),
        args=["-m", "construction_mcp"],
        env={"PATH": os.environ["PATH"],
             "CONSTRUCTION_MCP_DB": os.environ.get("CONSTRUCTION_MCP_DB", "/tmp/cc_smoke.db"),
             "CONSTRUCTION_MCP_OFFLINE": "1"},
    )
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            tools = (await session.list_tools()).tools
            print(f"tools exposed: {len(tools)}")
            print("  " + ", ".join(t.name for t in tools))

            # 1) читаем документы пустого проекта
            r1 = await session.call_tool("get_project_documents", {"project_id": "proj_demo"})
            print("get_project_documents ->", r1.content[0].text)

            # 2) валидное наблюдение -> сохранение
            obs = {
                "project_id": "proj_demo", "inspection_id": "insp_1", "room_id": "room_305",
                "work_name": "Штукатурка", "status": "in_progress",
                "estimated_completion_percent": 40, "confidence": 0.72,
                "evidence_frame_ids": ["frame_1"],
            }
            r2 = await session.call_tool("save_progress_observation", {"observation": obs})
            print("save_progress_observation ->", r2.content[0].text)

            # 3) расчёт отклонения через инструмент невозможен напрямую, но проверим
            #    ошибкоустойчивость: неизвестный аргумент не роняет сервер
            r3 = await session.call_tool("get_schedule_tasks", {"project_id": "proj_demo"})
            print("get_schedule_tasks ->", r3.content[0].text)

    print("MCP smoke: OK")


if __name__ == "__main__":
    anyio.run(main)

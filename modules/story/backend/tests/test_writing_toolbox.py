import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from app.routers.stories import create_writing_cards
from app.schemas.story import WritingAssistRequest


class WritingToolboxTests(unittest.IsolatedAsyncioTestCase):
    async def test_cards_use_the_authenticated_story_owner(self):
        db = SimpleNamespace(get=AsyncMock(return_value=None))
        story = SimpleNamespace(status="active", character_id=7, theme="森林")
        llm = SimpleNamespace(generate_writing_cards=AsyncMock(return_value=["第一条", "第二条", "第三条"]))
        with patch("app.routers.stories._get_story", new_callable=AsyncMock, return_value=story) as get_story, \
             patch("app.routers.stories.story_service.get_story_messages", new_callable=AsyncMock, return_value=[]), \
             patch("app.routers.stories.get_llm_service", return_value=llm):
            result = await create_writing_cards(12, WritingAssistRequest(tool="next"), "student-1", db)

        get_story.assert_awaited_once_with(12, "student-1", db)
        self.assertEqual(len(result.suggestions), 3)

from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Dict, Optional
import json

from core.config import (
    logger,
    SCENARIO_DIR,
    CLIPS_DIR,
)


@dataclass
class Scenario:
    """
    Represents a scripted dialog scenario.
    """

    name: str
    language: str
    description: str = ""
    wake_words: List[str] = field(default_factory=list)
    clips: List[Path] = field(default_factory=list)
    loop: bool = False

    @classmethod
    def from_dict(cls, data: Dict) -> "Scenario":

        if "name" not in data:
            raise ValueError("Scenario missing 'name'")

        if "language" not in data:
            raise ValueError("Scenario missing 'language'")

        return cls(
            name=data["name"],
            language=data["language"],
            description=data.get("description", ""),
            wake_words=data.get("wake_words", []),
            clips=[
                CLIPS_DIR / str(c)
                for c in data.get("clips", [])
            ],
            loop=data.get("loop", False),
        )


class ScenarioManager:
    """
    Loads and manages all chatbot scenarios.
    """

    def __init__(self):

        self.scenarios: Dict[str, Scenario] = {}

        self._wake_word_map: Dict[str, str] = {}

        self.load_all_scenarios()

    def load_all_scenarios(self):

        self.scenarios.clear()
        self._wake_word_map.clear()

        if not SCENARIO_DIR.exists():

            logger.warning(
                f"Scenario directory not found: {SCENARIO_DIR}"
            )
            return

        for json_file in SCENARIO_DIR.glob("*.json"):

            try:

                with open(
                    json_file,
                    "r",
                    encoding="utf-8",
                ) as f:

                    data = json.load(f)

                scenario = Scenario.from_dict(data)

                self.scenarios[scenario.name] = scenario

                for ww in scenario.wake_words:
                    self._wake_word_map[
                        ww.lower()
                    ] = scenario.name

                logger.info(
                    f"Loaded scenario: {scenario.name}"
                )

            except Exception:
                logger.exception(
                    f"Failed loading scenario: {json_file.name}"
                )

    def get_by_name(
        self,
        name: str,
    ) -> Optional[Scenario]:

        return self.scenarios.get(name)

    def get_by_wake_word(
        self,
        word: str,
    ) -> Optional[Scenario]:

        scenario_name = self._wake_word_map.get(
            word.lower()
        )

        if scenario_name:
            return self.scenarios.get(scenario_name)

        return None

    def get_greeting_scenario(
        self,
        language: str,
    ) -> Optional[Scenario]:

        return self.scenarios.get(
            f"greeting_{language}"
        )

    def list_scenarios(self) -> List[Scenario]:

        return list(self.scenarios.values())

    def all_wake_words(self) -> List[str]:

        return list(self._wake_word_map.keys())

    def add_scenario(
        self,
        data: Dict,
    ) -> bool:

        try:

            scenario = Scenario.from_dict(data)

            self.scenarios[scenario.name] = scenario

            for ww in scenario.wake_words:
                self._wake_word_map[
                    ww.lower()
                ] = scenario.name

            logger.info(
                f"Scenario added: {scenario.name}"
            )

            return True

        except Exception:
            logger.exception(
                "Failed to add scenario"
            )
            return False

    def delete_scenario(
        self,
        name: str,
    ) -> bool:

        if name not in self.scenarios:
            return False

        scenario = self.scenarios.pop(name)

        for ww in scenario.wake_words:

            if (
                self._wake_word_map.get(
                    ww.lower()
                )
                == name
            ):
                del self._wake_word_map[
                    ww.lower()
                ]

        logger.info(
            f"Scenario deleted: {name}"
        )

        return True

    @property
    def wake_word_map(self) -> Dict[str, str]:

        return self._wake_word_map
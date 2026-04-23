from dataclasses import dataclass
from typing import Optional

@dataclass
class Job:
    """
    Data model for a job listing extracted from various portals.
    """
    id: str
    title: str
    company: str
    location: str
    url: str
    description: str
    portal: str
    posted_date: Optional[str] = None
    score: Optional[float] = None
    status: str = "new"

    def __repr__(self) -> str:
        score_display = f"{self.score}/10" if self.score is not None else "N/A"
        return f"{self.title} @ {self.company} ({score_display})"

    def to_dict(self) -> dict:
        """
        Returns the job data as a plain dictionary.
        """
        return {k: v for k, v in self.__dict__.items() if not k.startswith('_')}

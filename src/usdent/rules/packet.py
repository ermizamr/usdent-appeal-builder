from __future__ import annotations

from dataclasses import dataclass
from typing import List


@dataclass
class PacketSection:
    title: str
    content: str


@dataclass
class PacketBundle:
    sections: List[PacketSection]
    attachments: List[str]


def assemble_packet(narrative: str, evidence_titles: List[str]) -> PacketBundle:
    sections = [
        PacketSection(title="Appeal Narrative", content=narrative),
        PacketSection(title="Evidence Checklist", content="\n".join(evidence_titles)),
    ]
    return PacketBundle(sections=sections, attachments=[])

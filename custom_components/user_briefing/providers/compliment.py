"""Compliment provider scaffold."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import voluptuous as vol

from ..models import SnippetResult
from .base_stub import StubBriefingProvider
from .registry import register_provider

_COMPLIMENTS = (
    "Today looks better already—you’re in it.",
    "Go make today earn the privilege of having you in it.",
    "You've survived every Monday so far. Impressive streak.",
    "Small steps still beat standing still.",
    "Your future self already appreciates today's effort.",
    "The sea is waiting, but first: conquer the land.",
    "Stay curious. Good things tend to follow.",
    "You're capable of more than your coffee thinks.",
    "Make at least one thing better today.",
    "Confidence looks good on you—wear it.",
    "Breathe in. Barcelona out.",
    "One good decision at a time.",
    "Today is another chance to surprise yourself.",
    "Keep going. Momentum is magic.",
    "Be the reason today turns out well.",
    "If all else fails, there's always billiards later.",
    "Your cue ball believes in you.",
    "Dive into today like it's crystal-clear water.",
    "You don't need perfect. You just need forward.",
    "Smile. It confuses the problems.",
    "Make waves, not excuses.",
    "Even a bad rack can become a great game.",
    "Stay calm and sink the next ball.",
    "Progress beats perfection every single time.",
    "You bring more to the table than you realize.",
    "Today's plot twist could be a good one.",
    "You've got this. Probably.",
    "The ocean doesn't rush, and neither should you.",
    "Keep your head above water—unless you're scuba diving.",
    "Win the day before it wins you.",
    "You are exactly one good decision away from a better day.",
    "Be kind. Be sharp. Be unstoppable.",
    "Make today worth remembering.",
    "Every expert once completely messed it up.",
    "You've handled worse. This one doesn't stand a chance.",
    "Your best break might not be on the pool table today.",
    "Remember: gravity is optional underwater.",
    "Stay positive. Negative buoyancy is for diving only.",
    "Be stubborn about your goals, flexible about your methods.",
    "Go create a story worth telling.",
    "You already have everything you need to begin.",
    "Start messy. Finish proud.",
    "The world rewards people who keep showing up.",
    "Luck tends to find prepared people.",
    "One smile can change the entire day.",
    "The coffee helps, but you're doing most of the work.",
    "You don't need permission to have a great day.",
    "Nobody else can do today quite like you.",
    "Go impress your future self.",
    "You've got momentum. Don't waste it.",
    "Today is a good day to outsmart yesterday.",
    "Success loves consistency.",
    "Make the ordinary extraordinary.",
    "Your resilience deserves more credit.",
    "Keep aiming. Even missed shots teach something.",
    "If life scratches, play safe and reset.",
    "Keep your cool. You're not a boiled octopus.",
    "Sea breeze mindset. Storm-proof attitude.",
    "Dive deep. Worry shallow.",
    "Good things rarely happen on the couch.",
    "Your biggest competition is yesterday's version of you.",
    "Keep moving. The map reveals itself on the way.",
    "One productive hour beats ten guilty ones.",
    "Make today ridiculously worthwhile.",
    "You make difficult things look easier than they are.",
    "Go collect little victories.",
    "Every day is training for something bigger.",
    "Trust yourself—you've been right before.",
    "The cue ball forgives. Learn to do the same.",
    "Your dive computer has fewer doubts than you do.",
    "Today owes you nothing. Go take something anyway.",
    "Stay humble. Stay hungry.",
    "Make someone smile today. Including yourself.",
    "You can absolutely handle what's coming.",
    "Tiny improvements compound into big wins.",
    "You don't have to feel motivated to get started.",
    "Keep your standards high and your shoulders relaxed.",
    "If today gets weird, lean into it.",
    "Barcelona called. It said enjoy the weather.",
    "Adventure starts after you leave the house.",
    "Your to-do list fears you.",
    "Make today's version of you proud.",
    'Great things often begin with "why not?".',
    "The world is full of opportunities disguised as effort.",
    "Focus on what you can control.",
    "Sink problems like corner-pocket shots.",
    "If you're overthinking, imagine you're underwater. Fewer emails there.",
    "Remember: sharks are less dangerous than unread Slack messages. Usually.",
    "Your confidence is your best equipment.",
    "You were built for interesting days.",
    "You didn't come this far to coast.",
    "Stay steady. Great things take time.",
    "Be brave enough to start.",
    "Today is another chapter, not the whole story.",
    "Chase progress, not applause.",
    "Don't let perfection bully productivity.",
    "You are dangerously close to having a fantastic day.",
    "Go make some future memories.",
    "Whatever happens today, you'll handle it.",
    'Now get out there—and try not to turn "just one game of billiards" into four.',
)


@register_provider
class ComplimentProvider(StubBriefingProvider):
    provider_key = "compliment"
    provider_name = "Compliment"

    def build_config_schema(self) -> vol.Schema:
        return vol.Schema({})

    def validate_config(self, user_input: dict[str, Any]) -> dict[str, Any]:
        return {}

    async def async_collect(self, config: dict[str, Any]) -> dict[str, Any]:
        index = datetime.now(UTC).timetuple().tm_yday % len(_COMPLIMENTS)
        return {"compliment": _COMPLIMENTS[index]}

    def normalize(self, payload: dict[str, Any], instance_id: str) -> SnippetResult:
        compliment = str(payload.get("compliment") or _COMPLIMENTS[0])
        return SnippetResult(
            provider_key=self.describe().key,
            instance_id=instance_id,
            status="ok",
            priority="optional",
            title=self.describe().name,
            text=compliment,
            scenario="compliment",
            data={"compliment": compliment},
        )

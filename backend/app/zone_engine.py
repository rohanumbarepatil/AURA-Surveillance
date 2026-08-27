from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class Zone:
    name: str
    x1: float
    y1: float
    x2: float
    y2: float

    def contains(self, x: float, y: float) -> bool:
        return (
            self.x1 <= x < self.x2
            and self.y1 <= y < self.y2
        )


@dataclass
class Detection:
    track_id: int
    class_id: int
    class_name: str
    confidence: float
    x1: int
    y1: int
    x2: int
    y2: int

    @property
    def center(self) -> tuple[float, float]:
        center_x = (self.x1 + self.x2) / 2
        center_y = (self.y1 + self.y2) / 2

        return center_x, center_y


class ZoneEngine:
    """
    Determines which surveillance zone
    a tracked detection belongs to.

    Current sandbox layout:

        ┌──────────────────────┬──────────────────────┐
        │    Cash Counter      │    Queue Corridor    │
        │      TOP LEFT        │      TOP RIGHT       │
        ├──────────────────────┼──────────────────────┤
        │    Main Entrance     │ Customer Waiting     │
        │    BOTTOM LEFT       │ Lounge               │
        │                      │ BOTTOM RIGHT         │
        └──────────────────────┴──────────────────────┘
    """

    def __init__(self, width: int, height: int):
        self.width = width
        self.height = height

        mid_x = width / 2
        mid_y = height / 2

        self.zones = [
            Zone(
                name="Cash Counter",
                x1=0,
                y1=0,
                x2=mid_x,
                y2=mid_y,
            ),
            Zone(
                name="Queue Corridor",
                x1=mid_x,
                y1=0,
                x2=width,
                y2=mid_y,
            ),
            Zone(
                name="Main Entrance",
                x1=0,
                y1=mid_y,
                x2=mid_x,
                y2=height,
            ),
            Zone(
                name="Customer Waiting Lounge",
                x1=mid_x,
                y1=mid_y,
                x2=width,
                y2=height,
            ),
        ]

    def get_zone(
        self,
        x: float,
        y: float,
    ) -> Optional[Zone]:

        for zone in self.zones:
            if zone.contains(x, y):
                return zone

        return None

    def get_zone_for_detection(
        self,
        detection: Detection,
    ) -> Optional[str]:

        center_x, center_y = detection.center

        zone = self.get_zone(center_x, center_y)

        if zone is None:
            return None

        return zone.name

    def process_detections(
        self,
        detections: list[Detection],
    ) -> list[dict]:

        results = []

        for detection in detections:

            center_x, center_y = detection.center

            zone = self.get_zone(
                center_x,
                center_y,
            )

            results.append(
                {
                    "track_id": detection.track_id,
                    "class_id": detection.class_id,
                    "class_name": detection.class_name,
                    "confidence": detection.confidence,
                    "bbox": [
                        detection.x1,
                        detection.y1,
                        detection.x2,
                        detection.y2,
                    ],
                    "center": [
                        center_x,
                        center_y,
                    ],
                    "zone": zone.name if zone else None,
                }
            )

        return results


def print_zones(width: int, height: int) -> None:

    engine = ZoneEngine(
        width=width,
        height=height,
    )

    print()
    print("=" * 60)
    print("AURA SURVEILLANCE - ZONE ENGINE")
    print("=" * 60)

    print(f"Frame resolution: {width} x {height}")
    print()

    for zone in engine.zones:
        print(
            f"{zone.name:28}"
            f" "
            f"({zone.x1:.0f}, {zone.y1:.0f})"
            f" -> "
            f"({zone.x2:.0f}, {zone.y2:.0f})"
        )

    print("=" * 60)


def run_test():

    width = 1270
    height = 720

    engine = ZoneEngine(
        width=width,
        height=height,
    )

    print_zones(
        width,
        height,
    )

    test_detections = [

        Detection(
            track_id=1,
            class_id=0,
            class_name="person",
            confidence=0.91,
            x1=100,
            y1=100,
            x2=200,
            y2=300,
        ),

        Detection(
            track_id=2,
            class_id=0,
            class_name="person",
            confidence=0.88,
            x1=800,
            y1=100,
            x2=900,
            y2=300,
        ),

        Detection(
            track_id=3,
            class_id=0,
            class_name="person",
            confidence=0.95,
            x1=100,
            y1=500,
            x2=200,
            y2=650,
        ),

        Detection(
            track_id=4,
            class_id=0,
            class_name="person",
            confidence=0.89,
            x1=800,
            y1=500,
            x2=900,
            y2=650,
        ),
    ]

    print()
    print("TEST DETECTIONS")
    print("-" * 60)

    results = engine.process_detections(
        test_detections
    )

    for result in results:

        print(
            f"Track ID: {result['track_id']:3}"
            f" | "
            f"Center: "
            f"({result['center'][0]:.1f}, "
            f"{result['center'][1]:.1f})"
            f" | "
            f"Zone: {result['zone']}"
        )

    print("-" * 60)
    print("Zone Engine test completed.")


if __name__ == "__main__":
    run_test()
# test.py
"""
Enhanced tests for the ECS.
Run with:  python test.py   or   pytest -q
"""

from dataclasses import dataclass
import asyncio, time
from ecs import World, System, AsyncSystem

# ---------------- Components ----------------
@dataclass
class Position:
    x: float
    y: float

@dataclass
class Velocity:
    vx: float
    vy: float

@dataclass
class Health:
    hp: int


# ---------------- Systems ----------------
class Physics(System):
    priority = 10
    def update(self, world: World, dt: float, **kwargs):
        for eid, (p, v) in world.view(Position, Velocity):
            p.x += v.vx * dt
            p.y += v.vy * dt

class Culling(System):
    priority = 5
    def update(self, world: World, bounds: float, **kwargs):
        with world.defer_deletions():
            for eid, p in world.iter_view(Position):
                if abs(p.x) > bounds or abs(p.y) > bounds:
                    world.destroy_entity(eid)

class Regen(AsyncSystem):
    priority = 7
    async def update(self, world: World, **kwargs):
        await asyncio.sleep(0.001)
        for eid, h in world.iter_view(Health):
            h.hp += 1

class SlowAsyncA(AsyncSystem):
    priority = 1
    async def update(self, world: World, **kwargs):
        await asyncio.sleep(0.05)

class SlowAsyncB(AsyncSystem):
    priority = 1
    async def update(self, world: World, **kwargs):
        await asyncio.sleep(0.05)

class SetupAsync(AsyncSystem):
    def __init__(self):
        self.ready = False
    async def setup(self, world: World):
        await asyncio.sleep(0.001)
        self.ready = True
    async def update(self, world: World, **kwargs):
        pass


# ---------------- Tests ----------------
def test_sync_update():
    w = World()
    w.add_system(Physics(), priority=10)

    e1 = w.create_entity(Position(0,0), Velocity(2,0))
    e2 = w.create_entity(Position(5,5))

    w.update(dt=0.5)
    p1 = w.get_component(e1, Position)
    p2 = w.get_component(e2, Position)

    assert (p1.x, p1.y) == (1.0, 0.0)
    assert (p2.x, p2.y) == (5.0, 5.0)

def test_archetype_move_and_snapshot():
    w = World()
    e = w.create_entity(Position(0,0))
    snap_before = w.view(Position)
    w.add_component(e, Velocity(1,0))
    snap_after = w.view(Position, Velocity)
    assert len(snap_before) == 1
    assert len(snap_after) == 1
    assert isinstance(snap_before[0][1], Position)

def test_component_replacement_invalidation():
    w = World()
    e = w.create_entity(Position(0,0))
    snap1 = w.view(Position)
    w.add_component(e, Position(10, 5))    # replace in-place; should invalidate cache
    snap2 = w.view(Position)
    assert snap1[0][1] != snap2[0][1]
    assert (snap2[0][1].x, snap2[0][1].y) == (10, 5)

def test_generation_counters_and_recycling():
    w = World()
    e1 = w.create_entity()
    w.destroy_entity(e1)
    assert not w.entity_exists(e1)
    # Recycle
    e2 = w.create_entity()
    assert e2 != e1            # generation bump implies a different handle
    try:
        w.get_component(e1, Position)
        assert False, "expected KeyError due to stale id"
    except KeyError:
        pass
    assert w.entity_count() == 1

def test_deferred_deletion_in_loop():
    w = World()
    e1 = w.create_entity(Position(100, 0))
    e2 = w.create_entity(Position(0, 0))
    with w.defer_deletions():
        for eid, p in w.iter_view(Position):
            if p.x > 50:
                w.destroy_entity(eid)  # deferred
    assert not w.entity_exists(e1) and w.entity_exists(e2)

def test_component_remove():
    w = World()
    e = w.create_entity(Position(1,2), Velocity(3,4))
    vel = w.remove_component(e, Velocity)
    assert isinstance(vel, Velocity)
    assert not w.has_component(e, Velocity)
    assert w.has_components(e, Position)

def test_system_order_and_timing():
    w = World()
    w.add_system(Physics(), priority=1)
    w.add_system(Culling(), priority=0)
    e = w.create_entity(Position(100,0), Velocity(-200,0))
    w.timed_update(dt=0.1, bounds=50)
    assert not w.entity_exists(e)
    assert "Physics" in w.process_times_ms

def test_entities_snapshot_and_iter():
    w = World()
    e1 = w.create_entity()
    e2 = w.create_entity(Position(0,0))
    snapped = set(w.entities())
    live = set(w.iter_entities())
    assert e1 in snapped and e2 in snapped
    assert e1 in live and e2 in live

def test_empty_component_view_is_empty():
    w = World()
    assert w.view(Health) == []

def test_clear_keeps_systems():
    w = World()
    phys = Physics()
    w.add_system(phys)
    w.create_entity(Position(0,0))
    w.clear()
    assert w.get_system(Physics) is phys
    # Systems still there; we can run update without error
    w.update(dt=0.01)

def test_async_update_and_setup_autocall():
    async def run():
        w = World()
        s = SetupAsync()
        w.add_system(s, priority=5)
        # setup should auto-run on first async update
        await w.aupdate()
        assert s.ready is True
    asyncio.run(run())

def test_async_concurrent_speedup():
    async def run():
        w = World()
        w.add_system(SlowAsyncA(), priority=3)
        w.add_system(SlowAsyncB(), priority=3)
        t0 = time.perf_counter()
        await w.aupdate_concurrent()
        t1 = time.perf_counter()
        elapsed = t1 - t0
        # Each task sleeps 0.05; concurrent should be ~0.05..0.08, not ~0.10+
        assert elapsed < 0.09, f"elapsed too long: {elapsed:.3f}s"
    asyncio.run(run())

def test_async_update_pipeline():
    async def run():
        w = World()
        w.add_system(Physics(), priority=5)
        w.add_system(Regen(), priority=5)

        e = w.create_entity(Position(0,0), Velocity(1,0), Health(10))
        await w.aupdate(dt=1.0)  # sync then async
        p = w.get_component(e, Position)
        h = w.get_component(e, Health)
        assert (p.x, p.y) == (1.0, 0.0)
        assert h.hp == 11
    asyncio.run(run())

if __name__ == "__main__":
    # Run all tests manually when executed as a script
    test_sync_update()
    test_archetype_move_and_snapshot()
    test_component_replacement_invalidation()
    test_generation_counters_and_recycling()
    test_deferred_deletion_in_loop()
    test_component_remove()
    test_system_order_and_timing()
    test_entities_snapshot_and_iter()
    test_empty_component_view_is_empty()
    test_clear_keeps_systems()
    test_async_update_and_setup_autocall()
    test_async_concurrent_speedup()
    test_async_update_pipeline()
    print("All tests passed.")

import json
from pathlib import Path
import sys
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from computer_inventory.database import make_engine, register_batch, DeviceRepository, dbapi_search
from computer_inventory.main import create_demo_devices


def main() -> None:
    path = Path(sys.argv[1]).resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    engine = make_engine("sqlite:///" + path.as_posix())
    with Session(engine) as session:
        if not DeviceRepository(session).all():
            session.rollback()
            register_batch(session, create_demo_devices())
    with Session(engine) as session:
        print(json.dumps(DeviceRepository(session).statistics(), indent=2))
        print("Dell:", [d.inventory_number for d in DeviceRepository(session).all("Dell")])
    with Session(engine) as session:
        try:
            register_batch(session, [create_demo_devices()[0]])
        except IntegrityError:
            print("Duplicate batch rolled back")
    print("DB-API:", dbapi_search(path, "INV-002"))
    engine.dispose()


if __name__ == "__main__":
    main()

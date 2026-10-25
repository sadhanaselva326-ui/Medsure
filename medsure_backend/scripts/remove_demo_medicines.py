"""remove_demo_medicines.py - Safely remove the 20 demo/benchmark medicine records
and all associated demo variants, identifiers, images, substitutes, demo alerts,
and demo-only manufacturers from MedSure Vision's live application database.

Preserves all official source-backed records (PMBI, NPPA, CDSCO).
"""

import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import select, delete, func
from app.database import AsyncSessionLocal
from app.models.medicine import MedicineMaster
from app.models.variant import MedicineVariant
from app.models.codes import MedicineIdentifier
from app.models.images import MedicineImage
from app.models.substitutes import MedicineSubstitute
from app.models.alerts import RegulatoryAlert
from app.models.manufacturer import Manufacturer
from app.models.sources import DataSource
from app.models.price import MedicinePrice


async def remove_demo_medicines():
    print("=" * 65)
    print("MEDSURE VISION — PURGING DEMO BENCHMARK DATA (PHASE 1)")
    print("=" * 65)

    async with AsyncSessionLocal() as session:
        # 1. Identify demo medicine IDs
        demo_meds_stmt = select(MedicineMaster).where(
            (MedicineMaster.is_demo == True) | (MedicineMaster.source_name == "demo_benchmark")
        )
        demo_meds = (await session.execute(demo_meds_stmt)).scalars().all()
        demo_med_ids = [m.medicine_id for m in demo_meds]
        print(f"Identified {len(demo_med_ids)} demo medicine records:")
        for m in demo_meds:
            print(f"  - {m.brand_name} (ID: {m.medicine_id})")

        # 2. Identify demo variant IDs
        demo_vars_stmt = select(MedicineVariant).where(
            (MedicineVariant.is_demo == True)
            | (MedicineVariant.medicine_id.in_(demo_med_ids))
            | (MedicineVariant.source_name == "demo_benchmark")
        )
        demo_vars = (await session.execute(demo_vars_stmt)).scalars().all()
        demo_var_ids = [v.variant_id for v in demo_vars]
        print(f"Identified {len(demo_var_ids)} demo variants.")

        # 3. Delete MedicineSubstitutes
        sub_stmt = select(MedicineSubstitute).where(
            (MedicineSubstitute.medicine_id.in_(demo_med_ids))
            | (MedicineSubstitute.substitute_medicine_id.in_(demo_med_ids))
        )
        subs = (await session.execute(sub_stmt)).scalars().all()
        for s in subs:
            await session.delete(s)
        print(f"Deleted {len(subs)} demo medicine substitutes.")

        # 4. Delete MedicineImages
        img_stmt = select(MedicineImage).where(MedicineImage.variant_id.in_(demo_var_ids))
        imgs = (await session.execute(img_stmt)).scalars().all()
        for img in imgs:
            await session.delete(img)
        print(f"Deleted {len(imgs)} demo medicine images.")

        # 5. Delete MedicineIdentifiers / Codes
        ident_stmt = select(MedicineIdentifier).where(
            (MedicineIdentifier.is_demo == True)
            | (MedicineIdentifier.variant_id.in_(demo_var_ids))
            | (MedicineIdentifier.source_name == "demo_benchmark")
        )
        idents = (await session.execute(ident_stmt)).scalars().all()
        for ident in idents:
            await session.delete(ident)
        print(f"Deleted {len(idents)} demo medicine identifiers/codes.")

        # 6. Delete Demo Regulatory Alerts
        alert_stmt = select(RegulatoryAlert).where(
            (RegulatoryAlert.is_demo == True)
            | (RegulatoryAlert.source_name == "demo_benchmark")
            | (RegulatoryAlert.medicine_id.in_(demo_med_ids))
        )
        alerts = (await session.execute(alert_stmt)).scalars().all()
        for a in alerts:
            await session.delete(a)
        print(f"Deleted {len(alerts)} demo regulatory alerts.")

        # 7. Delete Demo Variants
        for v in demo_vars:
            await session.delete(v)
        print(f"Deleted {len(demo_vars)} demo variants.")

        # 8. Delete Demo Medicines
        for m in demo_meds:
            await session.delete(m)
        print(f"Deleted {len(demo_meds)} demo medicine master records.")

        # 9. Clean up demo-only manufacturers
        all_mfgs = (await session.execute(select(Manufacturer))).scalars().all()
        deleted_mfgs_count = 0
        for mfg in all_mfgs:
            # Check remaining variants
            v_count = (await session.execute(
                select(func.count(MedicineVariant.variant_id)).where(MedicineVariant.manufacturer_id == mfg.manufacturer_id)
            )).scalar() or 0
            if v_count == 0 and (mfg.is_demo or mfg.source_name == "demo_benchmark"):
                await session.delete(mfg)
                deleted_mfgs_count += 1
                print(f"  Removed demo-only manufacturer: {mfg.name}")
        print(f"Deleted {deleted_mfgs_count} demo-only manufacturers.")

        # 10. Update DataSource coverage counts
        sources = (await session.execute(select(DataSource))).scalars().all()
        for s in sources:
            cnt = (await session.execute(
                select(func.count(MedicineMaster.medicine_id)).where(
                    (MedicineMaster.source_name == s.source_name) & (MedicineMaster.is_demo == False)
                )
            )).scalar() or 0
            if cnt == 0:
                cnt = (await session.execute(
                    select(func.count(RegulatoryAlert.alert_id)).where(
                        (RegulatoryAlert.source_name == s.source_name) & (RegulatoryAlert.is_demo == False)
                    )
                )).scalar() or 0
            s.coverage_count = cnt

        await session.commit()
        print("Database commit successful!")

        # 11. Final verification of remaining records
        remaining_meds = (await session.execute(select(func.count(MedicineMaster.medicine_id)))).scalar()
        remaining_real = (await session.execute(select(func.count(MedicineMaster.medicine_id)).where(MedicineMaster.is_demo == False))).scalar()
        remaining_demo = (await session.execute(select(func.count(MedicineMaster.medicine_id)).where(MedicineMaster.is_demo == True))).scalar()
        remaining_vars = (await session.execute(select(func.count(MedicineVariant.variant_id)))).scalar()
        remaining_mfgs = (await session.execute(select(func.count(Manufacturer.manufacturer_id)))).scalar()
        remaining_idents = (await session.execute(select(func.count(MedicineIdentifier.identifier_id)))).scalar()
        remaining_alerts = (await session.execute(select(func.count(RegulatoryAlert.alert_id)))).scalar()

        print("\n" + "=" * 65)
        print("POST-PURGE DATABASE COUNTS (ACTUAL DATABASE):")
        print(f"  Total Medicines:     {remaining_meds} (Real: {remaining_real}, Demo: {remaining_demo})")
        print(f"  Total Variants:      {remaining_vars}")
        print(f"  Total Manufacturers: {remaining_mfgs}")
        print(f"  Total Identifiers:   {remaining_idents}")
        print(f"  Regulatory Alerts:   {remaining_alerts}")
        print("=" * 65)

if __name__ == "__main__":
    asyncio.run(remove_demo_medicines())

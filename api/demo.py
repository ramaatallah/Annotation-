"""Verification script demonstrating the end-to-end Arabic NLP output."""

import sys
import asyncio

# Force UTF-8 encoding on standard output for Windows console
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

from app.services.nlp.pipeline import nlp_pipeline


async def main():
    sample_text = "جامعة النجاح الوطنية تقع في مدينة نابلس"
    print("\n" + "=" * 60)
    print(f"INPUT TEXT: {sample_text}")
    print("=" * 60)

    result = await nlp_pipeline.analyze_text(sample_text)

    print("\n--- DETECTED ENTITIES & TRILATERAL ROOTS ---")
    for entity in result["entities"]:
        print(f"\n[Entity]  : {entity['text']}")
        print(f" Category: {entity['category']}")
        print(f" Conf    : {entity['confidence']}")
        print(f" Span    : [{entity['start_char']}:{entity['end_char']}]")
        print(" Roots   :")
        for r in entity["roots"]:
            print(f"   * {r['word']} ──> {r['root']} (Trilateral: {r['is_trilateral']})")

    print("\n--- ALL WORDS TRILATERAL ROOTS ---")
    for r in result["all_roots"]:
        print(f"  {r['word']:<12} ──> {r['root']}")

    print(f"\nProcessing Time: {result['processing_time_ms']} ms")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    asyncio.run(main())

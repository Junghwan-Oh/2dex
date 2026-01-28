#!/usr/bin/env python3
"""
Fix duplicate sections in DEX_INTEGRATION_FRAMEWORK.md
"""

def fix_duplicates():
    with open("DEX_INTEGRATION_FRAMEWORK.md", 'r', encoding='utf-8') as f:
        content = f.read()

    # 1. Fix v2.0 Update duplicates (line 14-16)
    content = content.replace(
        '''- **Apex**: Framework refinement (saved 13 hours + 3 weeks)
- **v2.0 Update**: Added strategy selection, point farming validation, multi-DEX scaling
- **v2.0 Update**: Added strategy selection, point farming validation, multi-DEX scaling
- **v2.0 Update**: Added strategy selection, point farming validation, multi-DEX scaling''',
        '''- **Apex**: Framework refinement (saved 13 hours + 3 weeks)
- **v2.0 Update**: Added strategy selection, point farming validation, multi-DEX scaling
- **v2.1 Update**: DN strategy 2 approaches, Lighter API constraint, Breakeven methodology
- **v2.2 Update**: DN popularity explanation, MM research process, detailed breakeven guides'''
    )

    # 2. Find and analyze duplicate sections
    lines = content.split('\n')

    # Check for "Why DN is Most Popular" - appears at line 476 and 1069
    dn_pop_count = content.count('#### Why DN is Most Popular in Volume Farming')
    mm_research_count = content.count('### Market Making DEX Research Process')

    print(f"Found duplicates:")
    print(f"  - 'Why DN is Most Popular': {dn_pop_count} occurrences (should be 1)")
    print(f"  - 'MM Research Process': {mm_research_count} occurrences (should be 1)")

    # Keep only the FIRST occurrence of each section
    # This requires more sophisticated parsing

    # Strategy: Find section boundaries and remove duplicates
    dn_marker = '####Why DN is Most Popular in Volume Farming'
    mm_marker = '### Market Making DEX Research Process'

    # Find first occurrence of DN section (line ~476)
    first_dn_pos = content.find('#### Why DN is Most Popular in Volume Farming')

    # Find second occurrence (line ~1069)
    second_dn_pos = content.find('#### Why DN is Most Popular in Volume Farming', first_dn_pos + 100)

    if second_dn_pos > 0:
        # Find where second DN section ends (next ### or #### section)
        # Search for next major section after second DN
        next_section_after_dn = content.find('\n### ', second_dn_pos + 10)
        if next_section_after_dn < 0:
            next_section_after_dn = content.find('\n#### ', second_dn_pos + 10)

        if next_section_after_dn > second_dn_pos:
            # Remove from second DN start to next section
            content = content[:second_dn_pos] + content[next_section_after_dn:]
            print(f"  ✅ Removed duplicate DN section (pos {second_dn_pos}-{next_section_after_dn})")

    # Find first occurrence of MM Research (line ~306)
    first_mm_pos = content.find('### Market Making DEX Research Process')

    # Find second occurrence (line ~899)
    second_mm_pos = content.find('### Market Making DEX Research Process', first_mm_pos + 100)

    if second_mm_pos > 0:
        # Find next major section
        next_section_after_mm = content.find('\n### ', second_mm_pos + 10)

        if next_section_after_mm > second_mm_pos:
            content = content[:second_mm_pos] + content[next_section_after_mm:]
            print(f"  ✅ Removed duplicate MM Research section (pos {second_mm_pos}-{next_section_after_mm})")

    # Save fixed version
    with open("DEX_INTEGRATION_FRAMEWORK.md", 'w', encoding='utf-8') as f:
        f.write(content)

    print("\n✅ Duplicates removed")

    # Verify
    with open("DEX_INTEGRATION_FRAMEWORK.md", 'r', encoding='utf-8') as f:
        new_content = f.read()

    final_dn_count = new_content.count('#### Why DN is Most Popular in Volume Farming')
    final_mm_count = new_content.count('### Market Making DEX Research Process')

    print(f"\nVerification:")
    print(f"  - 'Why DN is Most Popular': {final_dn_count} (should be 1) {'✅' if final_dn_count == 1 else '❌'}")
    print(f"  - 'MM Research Process': {final_mm_count} (should be 1) {'✅' if final_mm_count == 1 else '❌'}")

if __name__ == '__main__':
    fix_duplicates()

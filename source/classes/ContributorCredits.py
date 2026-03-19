"""
Credits data generator for ALTTP Randomizer.

This module generates the byte data for the credits tilemap, matching the
output of stats/credits.asm. The generated data can be used to override
the credits text dynamically from Python.
"""

import logging
from typing import List, Tuple, Optional
from enum import Enum

from Text import (
    GoldCreditMapper, GreenCreditMapper, RedCreditMapper,
    LargeCreditTopMapper, LargeCreditBottomMapper
)


class SmallColor(Enum):
    YELLOW = "yellow"
    GREEN = "green"
    RED = "red"


# Map SmallColor enum to existing Text.py mappers
SMALL_COLOR_MAPPERS = {
    SmallColor.YELLOW: GoldCreditMapper,
    SmallColor.GREEN: GreenCreditMapper,
    SmallColor.RED: RedCreditMapper,
}


class CreditsLine:
    """Represents a single credits line."""
    pass


class EmptyLine(CreditsLine):
    """An empty line (displays a single space character)."""
    pass


class BlankLine(CreditsLine):
    """A blank line (no data, just skipped)."""
    pass


class SmallCredits(CreditsLine):
    """Small text credits line."""
    def __init__(self, text: str, color: SmallColor):
        self.text = text
        self.color = color


class SmallCreditsMixed(CreditsLine):
    """Small text credits line with mixed colors."""
    def __init__(self, segments: List, default_color: SmallColor):
        self.segments = segments
        self.default_color = default_color


class BigCredits(CreditsLine):
    """Big text credits (centered, takes 2 line slots for top/bottom halves)."""
    def __init__(self, text: str):
        self.text = text


class BigCreditsLeft(CreditsLine):
    """Big text credits (left-aligned, takes 2 line slots for top/bottom halves)."""
    def __init__(self, text: str):
        self.text = text


class ArbitraryLine(CreditsLine):
    """An arbitrary line pointing to a fixed address."""
    def __init__(self, address: int):
        self.address = address


class ContributorCredits:
    """Generates credits byte data matching the ASM output."""
    
    # Special byte patterns
    EMPTY_LINE_DATA = bytes([0x00, 0x01, 0x9F])
    BLANK_LINE_DATA = bytes([0xFF])
    
    # Where our line data starts (SNES bank-relative address)
    LINE_DATA_START = 0x844C
    
    # Maximum address for line data (SNES bank-relative address)
    LINE_DATA_MAX = 0x9800
    
    # Maximum line data size in bytes
    MAX_LINE_DATA_SIZE = LINE_DATA_MAX - LINE_DATA_START  # 0x13B4 = 5044 bytes
    
    # Pointer table size: 400 entries * 2 bytes each = 800 bytes (0x320)
    POINTER_TABLE_SIZE = 400
    
    # Size limitation - default credits must be exactly 303 lines to match stats offset
    EXPECTED_DEFAULT_CREDITS_LINES = 303
    
    def __init__(self):
        self.lines: List[CreditsLine] = []
        self._line_data: List[bytes] = []
        
    def add_empty_line(self) -> 'ContributorCredits':
        """Add an empty line."""
        self.lines.append(EmptyLine())
        return self
    
    def add_blank_line(self) -> 'ContributorCredits':
        """Add a blank line."""
        self.lines.append(BlankLine())
        return self
    
    def add_small_credits(self, text: str, color: SmallColor) -> 'ContributorCredits':
        """Add a small credits line with the specified color."""
        self.lines.append(SmallCredits(text, color))
        return self
    
    def add_small_credits_mixed(self, segments: List, default_color: SmallColor) -> 'ContributorCredits':
        """Add a small credits line with mixed colors."""
        self.lines.append(SmallCreditsMixed(segments, default_color))
        return self
    
    def add_big_credits(self, text: str) -> 'ContributorCredits':
        """Add a centered big credits line (uses 2 line slots)."""
        self.lines.append(BigCredits(text))
        return self
    
    def add_big_credits_left(self, text: str) -> 'ContributorCredits':
        """Add a left-aligned big credits line (uses 2 line slots)."""
        self.lines.append(BigCreditsLeft(text))
        return self
    
    def add_arbitrary_line(self, address: int) -> 'ContributorCredits':
        """Add an arbitrary line pointing to a fixed address."""
        self.lines.append(ArbitraryLine(address))
        return self
    
    def _encode_small_text(self, text: str, color: SmallColor) -> bytes:
        """Encode small credits text using existing Text.py mappers."""
        mapper = SMALL_COLOR_MAPPERS[color]
        text_bytes = mapper.convert(text)
        x_pos = (32 - len(text)) // 2
        length = 2 * len(text) - 1
        return bytes([x_pos, length]) + text_bytes
    
    def _encode_small_text_mixed(self, segments: List, default_color: SmallColor) -> bytes:
        """Encode small credits text with mixed colors.
        
        Segments can be plain strings (use default_color) or (text, color) tuples.
        """
        # Normalize segments to (text, color) tuples
        normalized = []
        for seg in segments:
            if isinstance(seg, tuple):
                normalized.append(seg)
            else:
                normalized.append((seg, default_color))
        
        # Build the full text to calculate position
        full_text = ''.join(text for text, _ in normalized)
        x_pos = (32 - len(full_text)) // 2
        length = 2 * len(full_text) - 1
        
        # Encode each segment with its color
        text_bytes = bytearray()
        for text, color in normalized:
            mapper = SMALL_COLOR_MAPPERS[color]
            text_bytes.extend(mapper.convert(text))
        
        return bytes([x_pos, length]) + bytes(text_bytes)
    
    def _encode_big_text(self, text: str, centered: bool = True) -> Tuple[bytes, bytes]:
        """Encode big credits text (both top and bottom halves) using existing Text.py mappers."""
        x_pos = (32 - len(text)) // 2 if centered else 2
        length = 2 * len(text) - 1
        
        text_bytes_hi = LargeCreditTopMapper.convert(text)
        line_hi = bytes([x_pos, length]) + text_bytes_hi
        
        text_bytes_lo = LargeCreditBottomMapper.convert(text)
        line_lo = bytes([x_pos, length]) + text_bytes_lo
        
        return line_hi, line_lo
    
    def _build_line_data(self) -> Tuple[List[int], bytes]:
        """Build the line data bytes and pointers for all lines.
        
        Returns:
            Tuple of (pointers, line_content_data)
            - pointers: List of 16-bit pointers for each line slot
            - line_content_data: The actual line content bytes (including special entries at start)
        """
        pointers = []
        line_content = bytearray()
        
        # Start with the special entries at the beginning of line data
        # EMPTY_LINE_DATA at offset 0x844C (3 bytes: $00, $01, $9F)
        # BLANK_LINE_DATA at offset 0x844F (1 byte: $FF)
        empty_line_ptr = self.LINE_DATA_START
        line_content.extend(self.EMPTY_LINE_DATA)
        
        blank_line_ptr = self.LINE_DATA_START + len(self.EMPTY_LINE_DATA)
        line_content.extend(self.BLANK_LINE_DATA)
        
        # Now current_offset points after the special entries
        current_offset = self.LINE_DATA_START + len(self.EMPTY_LINE_DATA) + len(self.BLANK_LINE_DATA)
        
        for line in self.lines:
            if isinstance(line, EmptyLine):
                pointers.append(empty_line_ptr)
            elif isinstance(line, BlankLine):
                pointers.append(blank_line_ptr)
            elif isinstance(line, SmallCredits):
                pointers.append(current_offset)
                data = self._encode_small_text(line.text, line.color)
                line_content.extend(data)
                current_offset += len(data)
            elif isinstance(line, SmallCreditsMixed):
                pointers.append(current_offset)
                data = self._encode_small_text_mixed(line.segments, line.default_color)
                line_content.extend(data)
                current_offset += len(data)
            elif isinstance(line, BigCredits) or isinstance(line, BigCreditsLeft):
                line_hi, line_lo = self._encode_big_text(line.text, centered=(not isinstance(line, BigCreditsLeft)))
                pointers.append(current_offset)
                line_content.extend(line_hi)
                current_offset += len(line_hi)
                pointers.append(current_offset)
                line_content.extend(line_lo)
                current_offset += len(line_lo)
            elif isinstance(line, ArbitraryLine):
                # Use the fixed address directly
                pointers.append(line.address)
        
        return pointers, bytes(line_content)
    
    def generate(self) -> Tuple[bytes, bytes]:
        """
        Generate the credits data.
        
        Returns:
            Tuple of (pointer_table_data, line_content_data)
            - pointer_table_data: The 16-bit pointer table (400 entries = 800 bytes)
              to write at SNES $23812C (PC 0x11812C)
            - line_content_data: The actual line content bytes
              to write at SNES $23844C (PC 0x11844C)
        """
        pointers, line_content = self._build_line_data()
        
        # Check if line data exceeds allocated space
        if len(line_content) > self.MAX_LINE_DATA_SIZE:
            raise ValueError(
                f"Credits line data exceeds allocated space: {len(line_content)} bytes > "
                f"{self.MAX_LINE_DATA_SIZE} bytes (max address $23{self.LINE_DATA_MAX:04X})"
            )
        
        # Build the full pointer table (400 entries)
        pointer_table = bytearray()
        for i in range(self.POINTER_TABLE_SIZE):
            if i < len(pointers):
                ptr = pointers[i]
            else:
                ptr = self.LINE_DATA_START  # Empty line
            # Write as little-endian 16-bit
            pointer_table.append(ptr & 0xFF)
            pointer_table.append((ptr >> 8) & 0xFF)
        
        return bytes(pointer_table), line_content
    
    def get_line_count(self) -> int:
        """Get the total number of line slots used."""
        count = 0
        for line in self.lines:
            if isinstance(line, (BigCredits, BigCreditsLeft)):
                count += 2  # Big credits use 2 line slots
            else:
                count += 1
        return count


def build_default_credits(world, player) -> ContributorCredits:
    """
    Build the default credits matching the ASM file.
    
    This creates all the credits content from the original game staff
    through the randomizer contributors.
    
    Args:
        world: Used to check settings for conditional credits
        player: Player number
    """
    gen = ContributorCredits()
    
    # Original Game Staff
    gen.add_empty_line()
    gen.add_small_credits("ORIGINAL GAME STAFF", SmallColor.YELLOW)
    gen.add_blank_line()
    gen.add_blank_line()
    
    gen.add_small_credits("EXECUTIVE PRODUCER", SmallColor.GREEN)
    gen.add_blank_line()
    gen.add_big_credits("HIROSHI YAMAUCHI")
    gen.add_blank_line()
    gen.add_blank_line()
    
    gen.add_small_credits("PRODUCER", SmallColor.YELLOW)
    gen.add_blank_line()
    gen.add_big_credits("SHIGERU MIYAMOTO")
    gen.add_blank_line()
    gen.add_blank_line()
    
    gen.add_small_credits("DIRECTOR", SmallColor.RED)
    gen.add_blank_line()
    gen.add_big_credits("TAKASHI TEZUKA")
    gen.add_blank_line()
    gen.add_blank_line()
    
    gen.add_small_credits("SCRIPT WRITER", SmallColor.GREEN)
    gen.add_blank_line()
    gen.add_big_credits("KENSUKE TANABE")
    gen.add_blank_line()
    gen.add_blank_line()
    
    gen.add_small_credits("ASSISTANT DIRECTORS", SmallColor.YELLOW)
    gen.add_blank_line()
    gen.add_big_credits("YASUHISA YAMAMURA")
    gen.add_blank_line()
    gen.add_big_credits("YOICHI YAMADA")
    gen.add_blank_line()
    gen.add_blank_line()
    
    gen.add_small_credits("SCREEN GRAPHICS DESIGNERS", SmallColor.GREEN)
    gen.add_empty_line()
    gen.add_empty_line()
    
    gen.add_small_credits("OBJECT DESIGNERS", SmallColor.YELLOW)
    gen.add_blank_line()
    gen.add_big_credits("SOICHIRO TOMITA")
    gen.add_blank_line()
    gen.add_big_credits("TAKAYA IMAMURA")
    gen.add_blank_line()
    gen.add_blank_line()
    
    gen.add_small_credits("BACK GROUND DESIGNERS", SmallColor.YELLOW)
    gen.add_blank_line()
    gen.add_big_credits("MASANAO ARIMOTO")
    gen.add_blank_line()
    gen.add_big_credits("TSUYOSHI WATANABE")
    gen.add_blank_line()
    gen.add_blank_line()
    
    gen.add_small_credits("PROGRAM DIRECTOR", SmallColor.RED)
    gen.add_blank_line()
    gen.add_big_credits("TOSHIHIKO NAKAGO")
    gen.add_blank_line()
    gen.add_blank_line()
    
    gen.add_small_credits("MAIN PROGRAMMER", SmallColor.YELLOW)
    gen.add_blank_line()
    gen.add_big_credits("YASUNARI SOEJIMA")
    gen.add_blank_line()
    gen.add_blank_line()
    
    gen.add_small_credits("OBJECT PROGRAMMER", SmallColor.GREEN)
    gen.add_blank_line()
    gen.add_big_credits("KAZUAKI MORITA")
    gen.add_blank_line()
    gen.add_blank_line()
    
    gen.add_small_credits("PROGRAMMERS", SmallColor.YELLOW)
    gen.add_blank_line()
    gen.add_big_credits("TATSUO NISHIYAMA")
    gen.add_blank_line()
    gen.add_big_credits("YUICHI YAMAMOTO")
    gen.add_blank_line()
    gen.add_big_credits("YOSHIHIRO NOMOTO")
    gen.add_blank_line()
    gen.add_big_credits("EIJI NOTO")
    gen.add_blank_line()
    gen.add_big_credits("SATORU TAKAHATA")
    gen.add_blank_line()
    gen.add_big_credits("TOSHIO IWAWAKI")
    gen.add_blank_line()
    gen.add_big_credits("SHIGEHIRO KASAMATSU")
    gen.add_blank_line()
    gen.add_big_credits("YASUNARI NISHIDA")
    gen.add_blank_line()
    gen.add_blank_line()
    
    gen.add_small_credits("SOUND COMPOSER", SmallColor.RED)
    gen.add_blank_line()
    gen.add_big_credits("KOJI KONDO")
    gen.add_blank_line()
    gen.add_blank_line()
    
    gen.add_small_credits("COORDINATORS", SmallColor.GREEN)
    gen.add_blank_line()
    gen.add_big_credits("KEIZO KATO")
    gen.add_blank_line()
    gen.add_big_credits("TAKAO SHIMIZU")
    gen.add_blank_line()
    gen.add_blank_line()
    
    gen.add_small_credits("PRINTED ART WORK", SmallColor.YELLOW)
    gen.add_blank_line()
    gen.add_big_credits("YOICHI KOTABE")
    gen.add_blank_line()
    gen.add_big_credits("HIDEKI FUJII")
    gen.add_blank_line()
    gen.add_big_credits("YOSHIAKI KOIZUMI")
    gen.add_blank_line()
    gen.add_big_credits("YASUHIRO SAKAI")
    gen.add_blank_line()
    gen.add_big_credits("TOMOAKI KUROUME")
    gen.add_blank_line()
    gen.add_blank_line()
    
    gen.add_small_credits("SPECIAL THANKS TO", SmallColor.RED)
    gen.add_blank_line()
    gen.add_big_credits("NOBUO OKAJIMA")
    gen.add_blank_line()
    gen.add_big_credits("YASUNORI TAKETANI")
    gen.add_blank_line()
    gen.add_big_credits("KIYOSHI KODA")
    gen.add_blank_line()
    gen.add_big_credits("TAKAMITSU KUZUHARA")
    gen.add_blank_line()
    gen.add_big_credits("HIRONOBU KAKUI")
    gen.add_blank_line()
    gen.add_big_credits("SHIGEKI YAMASHIRO")
    gen.add_blank_line()
    
    gen.add_empty_line()
    gen.add_empty_line()
    gen.add_empty_line()
    gen.add_empty_line()
    
    # Randomizer Contributors
    gen.add_small_credits("RANDOMIZER CONTRIBUTORS", SmallColor.RED)
    gen.add_blank_line()
    gen.add_blank_line()
    
    gen.add_small_credits("ITEM RANDOMIZER", SmallColor.YELLOW)
    gen.add_blank_line()
    gen.add_big_credits("KATDEVSGAMES         VEETORP")
    gen.add_blank_line()
    gen.add_big_credits("CHRISTOSOWEN       DESSYREQT")
    gen.add_blank_line()
    gen.add_big_credits("SMALLHACKER           SYNACK")
    gen.add_blank_line()
    gen.add_blank_line()
    
    gen.add_small_credits("ENTRANCE RANDOMIZER", SmallColor.GREEN)
    gen.add_blank_line()
    gen.add_big_credits("AMAZINGAMPHAROS   LLCOOLDAVE")
    gen.add_blank_line()
    gen.add_big_credits("KEVINCATHCART    CASSIDYMOEN")
    gen.add_blank_line()
    gen.add_blank_line()
    
    gen.add_small_credits("ENEMY RANDOMIZER", SmallColor.YELLOW)
    gen.add_blank_line()
    gen.add_big_credits("ZARBY89  SOSUKE3  ENDEROFGAMES")
    gen.add_blank_line()
    gen.add_blank_line()
    
    gen.add_small_credits("DOOR RANDOMIZER", SmallColor.GREEN)
    gen.add_blank_line()
    gen.add_big_credits("AERINON            COMPILING")
    gen.add_blank_line()
    gen.add_blank_line()
    
    gen.add_small_credits("OVERWORLD RANDOMIZER", SmallColor.YELLOW)
    gen.add_blank_line()
    gen.add_big_credits("CODEMANN8            CATOBAT")
    gen.add_blank_line()
    gen.add_blank_line()
    
    gen.add_small_credits("FESTIVE RANDOMIZER", SmallColor.GREEN)
    gen.add_blank_line()
    if world.limited_run[player] == '2604':
        gen.add_big_credits("CODEMANN8            AERINON")
        gen.add_blank_line()
        gen.add_big_credits("HIIMCODY1      FISH_WAFFLE64")
    else:
        gen.add_big_credits("KAN                    TOTAL")
        gen.add_blank_line()
        gen.add_big_credits("CATOBAT            DINSAPHIR")
    gen.add_blank_line()
    gen.add_blank_line()
    
    gen.add_small_credits("SPRITE DEVELOPMENT", SmallColor.YELLOW)
    gen.add_blank_line()
    gen.add_big_credits("MATRETHEWEY      FISH_WAFFLE64")
    gen.add_blank_line()
    gen.add_big_credits("IBAZLY  ACHY  ARTHEAU  TWROXAS")
    gen.add_blank_line()
    gen.add_big_credits("GLAN    PLAGUEDONE   TARTHORON")
    gen.add_blank_line()
    gen.add_blank_line()
    
    gen.add_small_credits("YOUR SPRITE BY", SmallColor.GREEN)
    gen.add_blank_line()
    gen.add_arbitrary_line(0x8000)  # YourSpriteCreditsHi
    gen.add_arbitrary_line(0x801E)  # YourSpriteCreditsLo
    gen.add_blank_line()
    gen.add_blank_line()
    
    gen.add_small_credits("MSU SUPPORT", SmallColor.YELLOW)
    gen.add_blank_line()
    gen.add_big_credits("QWERTYMODO")
    gen.add_blank_line()
    gen.add_blank_line()
    
    gen.add_small_credits("PALETTE SHUFFLER", SmallColor.GREEN)
    gen.add_blank_line()
    gen.add_big_credits("NELSON AKA SWR")
    gen.add_blank_line()
    gen.add_blank_line()
    
    gen.add_small_credits("WEBSITE AND LOGO", SmallColor.YELLOW)
    gen.add_blank_line()
    gen.add_big_credits("HIIMCODY1           PLEASURE")
    gen.add_blank_line()
    gen.add_blank_line()
    
    gen.add_small_credits("SPECIAL THANKS", SmallColor.RED)
    gen.add_blank_line()
    gen.add_big_credits("SUPERSKUJ  EVILASH25  MYRAMONG")
    gen.add_blank_line()
    gen.add_big_credits("JOSHRTA  MATHONNAPKINS  PINKUS")
    gen.add_blank_line()
    gen.add_big_credits("WALKINGEYE  MICHAELK  YUZUHARA")
    gen.add_blank_line()
    gen.add_big_credits("EMOSARU  SAKURATSUBASA  FOUTON")
    gen.add_blank_line()
    gen.add_big_credits("BONTA   NEOMUFFINS")
    gen.add_blank_line()
    gen.add_big_credits("AND")
    gen.add_blank_line()
    gen.add_big_credits("THE ALTTP RANDOMIZER COMMUNITY")
    gen.add_blank_line()
    gen.add_blank_line()
    
    gen.add_small_credits("COMMUNITY DISCORD", SmallColor.GREEN)
    gen.add_blank_line()
    gen.add_big_credits("HTTPS://ALTTPR.COM/DISCORD")
    
    gen.add_empty_line()
    gen.add_empty_line()
    gen.add_empty_line()
    gen.add_empty_line()
    gen.add_empty_line()
    gen.add_empty_line()

    if world.limited_run[player] == '2604':
        gen.add_empty_line()
        gen.add_empty_line()
        gen.add_empty_line()
        gen.add_small_credits("IN MEMORY OF", SmallColor.RED)
        gen.add_blank_line()
        gen.add_big_credits("CASSIDYMOEN")
        gen.add_blank_line()
        gen.add_small_credits_mixed(["YOU BUILT PATHS WE ", ("STILL", SmallColor.RED), " WALK"], SmallColor.YELLOW)
        gen.add_small_credits_mixed(["YOUR ", ("PASSION", SmallColor.RED), " BRINGS US JOY"], SmallColor.YELLOW)
        gen.add_blank_line()
        gen.add_small_credits_mixed([("FOREVER", SmallColor.GREEN), " PART OF THE RANDOMIZER"], SmallColor.YELLOW)
    else:
        for _ in range(12):
            gen.add_empty_line()

    for _ in range(10):
        gen.add_empty_line()
    
    # Enforce exactly 303 lines for default credits (stats section starts at line 303)
    line_count = gen.get_line_count()
    if line_count != ContributorCredits.EXPECTED_DEFAULT_CREDITS_LINES:
        raise ValueError(
            f"Default credits must have exactly {ContributorCredits.EXPECTED_DEFAULT_CREDITS_LINES} lines, "
            f"but has {line_count} lines. Adjust empty lines to match."
        )
    
    return gen


def build_stats_credits() -> ContributorCredits:
    """
    Build the stats section of credits (line 304 onwards).
    """
    gen = ContributorCredits()
    
    gen.add_small_credits("THE IMPORTANT STUFF", SmallColor.YELLOW)
    gen.add_blank_line()
    gen.add_blank_line()
    
    gen.add_empty_line()
    gen.add_small_credits("TIME FOUND", SmallColor.GREEN)
    gen.add_blank_line()
    gen.add_blank_line()
    
    gen.add_big_credits_left("FIRST SWORD")
    gen.add_blank_line()
    gen.add_big_credits_left("PEGASUS BOOTS")
    gen.add_blank_line()
    gen.add_big_credits_left("FLUTE")
    gen.add_blank_line()
    gen.add_big_credits_left("MIRROR")
    gen.add_blank_line()
    gen.add_blank_line()
    
    gen.add_empty_line()
    gen.add_small_credits("BOSS KILLS", SmallColor.YELLOW)
    gen.add_blank_line()
    gen.add_blank_line()
    
    gen.add_big_credits_left("SWORDLESS                /13")
    gen.add_blank_line()
    gen.add_big_credits_left("FIGHTER'S SWORD          /13")
    gen.add_blank_line()
    gen.add_big_credits_left("MASTER SWORD             /13")
    gen.add_blank_line()
    gen.add_big_credits_left("TEMPERED SWORD           /13")
    gen.add_blank_line()
    gen.add_big_credits_left("GOLD SWORD               /13")
    gen.add_blank_line()
    gen.add_blank_line()
    
    gen.add_small_credits("GAME STATS", SmallColor.RED)
    gen.add_blank_line()
    gen.add_blank_line()
    
    gen.add_big_credits_left("DAMAGE TAKEN")
    gen.add_blank_line()
    gen.add_big_credits_left("MAGIC USED")
    gen.add_blank_line()
    gen.add_big_credits_left("BONKS")
    gen.add_blank_line()
    gen.add_big_credits_left("SAVE AND QUITS")
    gen.add_blank_line()
    gen.add_big_credits_left("DEATHS")
    gen.add_blank_line()
    gen.add_big_credits_left("FAERIE REVIVALS")
    gen.add_blank_line()
    gen.add_big_credits_left("TOTAL MENU TIME")
    gen.add_blank_line()
    gen.add_big_credits_left("TOTAL LAG TIME")
    gen.add_blank_line()
    gen.add_blank_line()
    
    gen.add_blank_line()
    gen.add_blank_line()
    gen.add_blank_line()
    gen.add_blank_line()
    gen.add_blank_line()
    gen.add_blank_line()
    gen.add_blank_line()
    
    gen.add_empty_line()
    gen.add_empty_line()
    gen.add_arbitrary_line(0x803C)  # CollectionRateHi
    gen.add_arbitrary_line(0x805A)  # CollectionRateLo
    gen.add_blank_line()
    
    gen.add_big_credits_left("TOTAL TIME")
    gen.add_blank_line()
    
    # Final empty lines
    for _ in range(6):
        gen.add_empty_line()
    
    return gen


def get_credits_data(world, player) -> Tuple[bytes, bytes]:
    """
    Generate complete credits data.
    
    Args:
        world: Used to check settings for conditional credits
    
    Returns:
        Tuple of (pointer_table_data, line_content_data)
    """
    main_credits = build_default_credits(world, player)
    stats_credits = build_stats_credits()
    
    # Generate main credits (lines 1-303)
    main_ptr_table, main_line_data = main_credits.generate()
    
    # Generate stats credits (lines 304+)
    # Need to adjust pointers for stats section to account for main line data
    stats_pointers, stats_line_data = stats_credits._build_line_data()
    
    # Calculate the empty/blank line pointers (at start of main_line_data)
    empty_line_ptr = ContributorCredits.LINE_DATA_START
    blank_line_ptr = ContributorCredits.LINE_DATA_START + len(ContributorCredits.EMPTY_LINE_DATA)
    
    # Adjust stats pointers - they need to be offset by the main line data size
    # But subtract the special entries size since stats_line_data also includes them
    special_entries_size = len(ContributorCredits.EMPTY_LINE_DATA) + len(ContributorCredits.BLANK_LINE_DATA)
    main_line_data_size = len(main_line_data) - special_entries_size
    adjusted_stats_pointers = []
    for ptr in stats_pointers:
        if ptr == empty_line_ptr or ptr == blank_line_ptr or ptr < 0x8450:
            # Keep references to special entries as-is
            adjusted_stats_pointers.append(ptr)
        else:
            # Adjust by main data size
            adjusted_stats_pointers.append(ptr + main_line_data_size)
    
    # Build combined pointer table
    all_pointers = []
    # First, extract pointers from main credits
    main_pointers, _ = main_credits._build_line_data()
    all_pointers.extend(main_pointers)
    all_pointers.extend(adjusted_stats_pointers)
    
    # Build the full pointer table (400 entries)
    pointer_table = bytearray()
    for i in range(ContributorCredits.POINTER_TABLE_SIZE):
        if i < len(all_pointers):
            ptr = all_pointers[i]
        else:
            ptr = 0x0000  # Unused entries
        # Write as little-endian 16-bit
        pointer_table.append(ptr & 0xFF)
        pointer_table.append((ptr >> 8) & 0xFF)
    
    # Combine line data (skip special entries from stats since main already has them)
    all_line_data = main_line_data + stats_line_data[special_entries_size:]
    
    # Check if combined line data exceeds allocated space
    if len(all_line_data) > ContributorCredits.MAX_LINE_DATA_SIZE:
        raise ValueError(
            f"Combined credits line data exceeds allocated space: {len(all_line_data)} bytes > "
            f"{ContributorCredits.MAX_LINE_DATA_SIZE} bytes (max address $23{ContributorCredits.LINE_DATA_MAX:04X})"
        )
    
    return bytes(pointer_table), all_line_data


if __name__ == "__main__":
    # Test the generator
    logger = logging.getLogger('')
    
    # Create mock world and player for testing
    class MockWorld:
        def __init__(self):
            self.limited_run = {1: '2604'}
            pass
    
    world = MockWorld()
    player = 1
    
    gen = build_default_credits(world, player)
    line_count = gen.get_line_count()
    logger.info(f"Main credits line count: {line_count}")
    logger.info(f"Expected: 303 (before stats section)")
    
    ptr_table, line_data = gen.generate()
    logger.info(f"Generated {len(ptr_table)} bytes of pointer table")
    logger.info(f"Generated {len(line_data)} bytes of line data")
    
    stats_gen = build_stats_credits()
    stats_line_count = stats_gen.get_line_count()
    logger.info(f"Stats section line count: {stats_line_count}")
    
    # Test full generation
    full_ptr_table, full_line_data = get_credits_data(world, player)
    logger.info(f"Full pointer table: {len(full_ptr_table)} bytes")
    logger.info(f"Full line data: {len(full_line_data)} bytes")

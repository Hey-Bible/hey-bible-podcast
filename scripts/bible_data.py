"""WEB Bible verse counts - 66 books total"""

# Format: book_name: {chapters: [verse_count, verse_count, ...]}
BIBLE_STRUCTURE = {
    # Old Testament
    "genesis": {"chapters": [31, 25, 24, 26, 32, 22, 24, 22, 29, 32, 32, 20, 18, 24, 21, 16, 27, 33, 38, 18, 34, 24, 20, 67, 34, 35, 46, 22, 35, 43, 55, 32, 20, 31, 29, 43, 36, 30, 23, 23, 57, 38, 34, 34, 28, 34, 31, 22, 33, 26]},
    "exodus": {"chapters": [22, 25, 22, 31, 23, 30, 25, 32, 35, 29, 10, 51, 22, 31, 27, 36, 16, 27, 25, 26, 36, 31, 33, 18, 40, 37, 21, 43, 46, 38, 18, 35, 23, 35, 35, 38, 29, 31, 43, 38]},
    "leviticus": {"chapters": [17, 16, 17, 35, 19, 30, 38, 36, 24, 20, 47, 8, 59, 57, 33, 34, 16, 30, 37, 27, 24, 33, 44, 23, 55, 46, 34]},
    "numbers": {"chapters": [54, 34, 51, 49, 31, 27, 89, 26, 23, 36, 35, 16, 33, 45, 41, 50, 13, 32, 22, 29, 35, 41, 30, 25, 18, 65, 23, 31, 40, 16, 54, 42, 56, 29, 34, 13]},
    "deuteronomy": {"chapters": [46, 37, 29, 49, 33, 25, 26, 20, 29, 22, 32, 32, 18, 29, 23, 22, 20, 22, 21, 20, 23, 30, 25, 22, 19, 19, 26, 68, 29, 20, 30, 52, 29, 12]},
    "joshua": {"chapters": [18, 24, 17, 24, 15, 27, 26, 35, 27, 43, 23, 24, 33, 15, 63, 10, 18, 28, 51, 9, 45, 34, 16, 33]},
    "judges": {"chapters": [36, 23, 31, 24, 31, 40, 25, 35, 57, 18, 40, 15, 25, 20, 20, 31, 13, 31, 30, 31, 25, 24, 33, 25, 5, 31, 40, 25, 35, 20, 25, 31, 22, 28, 33, 13, 31, 26, 30]},
    "ruth": {"chapters": [22, 23, 18, 22]},
    "1-samuel": {"chapters": [28, 36, 21, 22, 12, 21, 17, 22, 27, 25, 12, 25, 23, 52, 35, 23, 58, 30, 24, 42, 15, 23, 29, 22, 44, 25, 12, 25, 11, 31, 13]},
    "2-samuel": {"chapters": [27, 32, 39, 12, 25, 23, 29, 18, 13, 19, 27, 31, 39, 33, 37, 23, 29, 33, 43, 26, 22, 51, 39, 25]},
    "1-kings": {"chapters": [53, 46, 28, 34, 18, 38, 51, 66, 28, 29, 43, 33, 34, 31, 34, 34, 24, 46, 21, 43, 29, 53]},
    "2-kings": {"chapters": [18, 25, 27, 44, 27, 33, 20, 29, 37, 36, 21, 21, 25, 29, 38, 20, 41, 37, 37, 21, 26, 20, 37, 20, 30]},
    "1-chronicles": {"chapters": [54, 55, 24, 43, 26, 81, 40, 40, 44, 14, 47, 40, 14, 17, 29, 43, 27, 17, 19, 8, 30, 19, 32, 31, 31, 32, 34, 21, 30]},
    "2-chronicles": {"chapters": [17, 18, 17, 22, 14, 42, 22, 18, 31, 19, 23, 16, 22, 15, 19, 14, 19, 34, 11, 37, 20, 12, 21, 25, 28, 23, 9, 27, 36, 27, 21, 33, 25, 33, 27, 23]},
    "ezra": {"chapters": [11, 70, 13, 24, 17, 22, 28, 36, 15, 44]},
    "nehemiah": {"chapters": [11, 20, 32, 23, 19, 19, 73, 18, 38, 39, 36, 47, 31]},
    "esther": {"chapters": [22, 23, 15, 17, 14, 14, 10, 17, 32, 3]},
    "job": {"chapters": [22, 13, 26, 21, 27, 30, 21, 22, 35, 22, 20, 25, 28, 22, 35, 22, 16, 21, 29, 29, 34, 30, 17, 25, 6, 14, 23, 28, 25, 31, 40, 22, 33, 37, 16, 33, 24, 41, 30, 24, 34, 17]},
    "psalms": {"chapters": [6, 12, 8, 8, 12, 10, 17, 9, 20, 18, 7, 8, 6, 7, 5, 11, 15, 50, 14, 9, 13, 31, 6, 10, 22, 12, 14, 9, 11, 12, 24, 11, 22, 22, 28, 12, 40, 22, 13, 17, 13, 11, 5, 26, 17, 11, 9, 14, 20, 23, 19, 9, 6, 7, 23, 13, 11, 11, 17, 12, 8, 12, 11, 10, 13, 11, 7, 20, 10, 12, 15, 21, 10, 20, 17, 9, 7, 20, 13, 18, 10, 8, 19, 13, 14, 17, 7, 19, 53, 17, 16, 16, 5, 23, 11, 13, 12, 9, 9, 5, 8, 28, 22, 35, 45, 48, 43, 13, 31, 7, 10, 10, 9, 8, 18, 19, 2, 29, 176, 7, 8, 9, 4, 8, 5, 6, 5, 6, 8, 8, 3, 18, 3, 3, 21, 26, 9, 8, 24, 13, 10, 7, 12, 15, 21, 10, 20, 14, 9, 6]},
    "proverbs": {"chapters": [33, 22, 35, 27, 23, 35, 27, 36, 18, 32, 31, 28, 25, 35, 33, 33, 28, 24, 29, 30, 31, 29, 35, 34, 28, 28, 27, 28, 27, 33, 31]},
    "ecclesiastes": {"chapters": [18, 26, 22, 16, 20, 12, 29, 17, 18, 20, 10, 14]},
    "song-of-solomon": {"chapters": [17, 17, 11, 16, 16, 13, 13, 14]},
    "isaiah": {"chapters": [31, 22, 26, 6, 30, 13, 25, 22, 21, 34, 16, 6, 22, 32, 9, 14, 14, 7, 25, 6, 17, 25, 18, 23, 12, 21, 13, 29, 24, 33, 9, 20, 24, 17, 10, 22, 38, 22, 8, 31, 29, 25, 28, 28, 25, 13, 15, 22, 26, 11, 23, 15, 12, 17, 13, 12, 21, 14, 21, 22, 11, 12, 19, 12, 25, 24]},
    "jeremiah": {"chapters": [19, 37, 25, 31, 31, 30, 34, 22, 26, 25, 23, 17, 27, 22, 21, 21, 27, 23, 15, 18, 14, 30, 40, 10, 38, 24, 22, 17, 32, 24, 40, 44, 26, 22, 19, 32, 21, 28, 18, 16, 18, 22, 13, 30, 5, 28, 7, 47, 39, 46, 64, 34]},
    "lamentations": {"chapters": [22, 22, 66, 22, 22]},
    "ezekiel": {"chapters": [28, 10, 27, 17, 17, 14, 27, 18, 11, 22, 25, 28, 23, 23, 8, 63, 24, 32, 14, 49, 32, 31, 49, 27, 17, 21, 36, 26, 21, 26, 18, 32, 33, 31, 15, 38, 28, 23, 29, 49, 26, 20, 27, 31, 25, 24, 23, 35]},
    "daniel": {"chapters": [21, 49, 30, 37, 31, 28, 28, 27, 27, 21, 45, 13]},
    "hosea": {"chapters": [11, 23, 5, 19, 15, 11, 16, 14, 17, 15, 12, 14, 16, 9]},
    "joel": {"chapters": [20, 32, 21]},
    "amos": {"chapters": [15, 16, 15, 13, 27, 14, 17, 14, 15]},
    "obadiah": {"chapters": [21]},
    "jonah": {"chapters": [17, 10, 10, 11]},
    "micah": {"chapters": [16, 13, 12, 13, 15, 16, 20]},
    "nahum": {"chapters": [15, 13, 19]},
    "habakkuk": {"chapters": [17, 20, 19]},
    "zephaniah": {"chapters": [18, 15, 20]},
    "haggai": {"chapters": [15, 23]},
    "zechariah": {"chapters": [21, 13, 10, 14, 11, 15, 14, 22, 17, 12, 17, 14, 9, 21]},
    "malachi": {"chapters": [14, 17, 18, 6]},
    
    # New Testament
    "matthew": {"chapters": [25, 23, 17, 25, 48, 34, 29, 34, 38, 42, 30, 50, 58, 36, 39, 28, 27, 35, 30, 34, 46, 46, 39, 51, 46, 75, 66, 20]},
    "mark": {"chapters": [45, 28, 35, 41, 43, 56, 37, 38, 50, 52, 33, 44, 37, 72, 47, 20]},
    "luke": {"chapters": [80, 52, 38, 44, 39, 49, 50, 56, 62, 42, 54, 59, 35, 35, 32, 31, 37, 43, 48, 47, 38, 71, 56, 53]},
    "john": {"chapters": [51, 25, 36, 54, 47, 71, 53, 59, 41, 42, 57, 50, 38, 31, 27, 33, 26, 40, 42, 31, 25]},
    "acts": {"chapters": [26, 47, 26, 37, 42, 15, 60, 40, 43, 48, 30, 25, 52, 28, 41, 40, 34, 28, 41, 38, 40, 30, 35, 27, 27, 32, 44, 31]},
    "romans": {"chapters": [32, 29, 31, 25, 21, 23, 25, 39, 33, 21, 36, 21, 14, 23, 33, 27]},
    "1-corinthians": {"chapters": [31, 16, 23, 21, 13, 20, 40, 13, 27, 33, 34, 31, 13, 40, 58, 24]},
    "2-corinthians": {"chapters": [24, 17, 18, 18, 21, 13, 16, 24, 15, 18, 33, 21, 14]},
    "galatians": {"chapters": [24, 21, 29, 31, 26, 18]},
    "ephesians": {"chapters": [23, 22, 21, 32, 33, 24]},
    "philippians": {"chapters": [30, 30, 21, 23]},
    "colossians": {"chapters": [29, 23, 25, 18]},
    "1-thessalonians": {"chapters": [10, 20, 13, 18, 28]},
    "2-thessalonians": {"chapters": [12, 17, 18]},
    "1-timothy": {"chapters": [20, 15, 16, 16, 25, 21]},
    "2-timothy": {"chapters": [18, 26, 17, 22]},
    "titus": {"chapters": [16, 15, 15]},
    "philemon": {"chapters": [25]},
    "hebrews": {"chapters": [14, 18, 19, 16, 14, 20, 28, 13, 28, 39, 40, 29, 25]},
    "james": {"chapters": [27, 26, 18, 17, 20]},
    "1-peter": {"chapters": [25, 25, 22, 19, 14]},
    "2-peter": {"chapters": [21, 22, 18]},
    "1-john": {"chapters": [10, 29, 24, 21, 21]},
    "2-john": {"chapters": [13]},
    "3-john": {"chapters": [15]},
    "jude": {"chapters": [25]},
    "revelation": {"chapters": [20, 29, 22, 11, 14, 17, 17, 13, 21, 11, 19, 18, 18, 20, 8, 21, 18, 24, 21, 15, 27, 21]},
}

# Ordered list of all books
BOOK_ORDER = list(BIBLE_STRUCTURE.keys())

def get_book_index(book_name: str) -> int:
    """Get the index of a book in canonical order"""
    return BOOK_ORDER.index(book_name.lower())

def get_next_book_chapter_verse(current_book: str, current_chapter: int, current_verse: int):
    """Get the next verse position"""
    book = current_book.lower()
    chapters = BIBLE_STRUCTURE[book]["chapters"]
    
    # Check if there's another verse in this chapter
    if current_verse < chapters[current_chapter - 1]:
        return book, current_chapter, current_verse + 1
    
    # Check if there's another chapter in this book
    if current_chapter < len(chapters):
        return book, current_chapter + 1, 1
    
    # Move to next book
    current_idx = get_book_index(book)
    if current_idx < len(BOOK_ORDER) - 1:
        next_book = BOOK_ORDER[current_idx + 1]
        return next_book, 1, 1
    
    # End of Bible
    return None, None, None

def get_total_verse_count():
    """Calculate total verses in Bible"""
    total = 0
    for book in BOOK_ORDER:
        for chapter_verses in BIBLE_STRUCTURE[book]["chapters"]:
            total += chapter_verses
    return total

if __name__ == "__main__":
    print(f"Total verses in WEB Bible: {get_total_verse_count():,}")
    print(f"Total books: {len(BOOK_ORDER)}")

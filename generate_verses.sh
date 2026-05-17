#!/bin/bash

VENICE_API_KEY="VENICE-INFERENCE-KEY-WGD74Sc663fbvu59-em7RzqgHkB90tx06_kLqT91c9"
BASE_DIR="/root/.openclaw/workspace-claudius/hey-bible-podcast"
TARGET_COUNT=200
START_BOOK="joshua"
START_CHAPTER=15
START_VERSE=14

# Track current position
current_book="$START_BOOK"
current_chapter=$START_CHAPTER
current_verse=$START_VERSE
generated_count=0

# Function to get verse count for a chapter
get_verse_count() {
    local book=$1
    local chapter=$2
    local url="https://bible-api.com/${book}+${chapter}"
    local response=$(curl -s "$url")
    echo "$response" | jq -r '.verses | length'
}

# Function to fetch verse text
get_verse_text() {
    local book=$1
    local chapter=$2
    local verse=$3
    local url="https://bible-api.com/${book}+${chapter}:${verse}?translation=web"
    local response=$(curl -s "$url")
    echo "$response" | jq -r '.text' | sed 's/^[[:space:]]*//'
}

# Function to generate TTS
generate_tts() {
    local text="$1"
    local output_file="$2"

    curl -s -X POST "https://api.venice.ai/v1/audio/speech" \
        -H "Authorization: Bearer $VENICE_API_KEY" \
        -H "Content-Type: application/json" \
        -d "{
            \"model\": \"tts-elevenlabs-turbo-v2-5\",
            \"voice\": \"Bill\",
            \"input\": \"$text\"
        }" \
        --output "$output_file"
}

# Function to update progress
update_progress() {
    local book=$1
    local chapter=$2
    local verse=$3
    local completed=$4
    local completed_chapter="$book-$chapter"

    local temp_file=$(mktemp)
    jq --arg book "$book" \
       --arg chapter "$chapter" \
       --arg verse "$verse" \
       --arg completed "$completed" \
       --arg completed_chapter "$completed_chapter" \
       '.book = $book |
        .chapter = ($chapter | tonumber) |
        .verse = ($verse | tonumber) |
        .completed_count = ($completed | tonumber) |
        .last_run = now | todate |
        if (.completed_chapters | index($completed_chapter)) then . else .completed_chapters += [$completed_chapter] end' \
       "$BASE_DIR/state/progress.json" > "$temp_file" && mv "$temp_file" "$BASE_DIR/state/progress.json"
}

# Main loop
echo "Starting TTS generation from $current_book $current_chapter:$current_verse"
echo "Target: $TARGET_COUNT verses"

while [ $generated_count -lt $TARGET_COUNT ]; do
    # Get verse text
    verse_text=$(get_verse_text "$current_book" "$current_chapter" "$current_verse")

    if [ -z "$verse_text" ] || [ "$verse_text" = "null" ]; then
        echo "No more verses at $current_book $current_chapter:$current_verse"
        break
    fi

    # Create directory if needed
    mkdir -p "$BASE_DIR/books/$current_book/$current_chapter"

    # Generate output filename
    output_file="$BASE_DIR/books/$current_book/$current_book-$current_chapter-$current_verse-web.mp3"

    # Skip if already exists
    if [ -f "$output_file" ]; then
        echo "[$generated_count/$TARGET_COUNT] Skipping existing: $current_book $current_chapter:$current_verse"
    else
        # Generate TTS
        echo "[$generated_count/$TARGET_COUNT] Generating: $current_book $current_chapter:$current_verse"
        generate_tts "$verse_text" "$output_file"

        # Check if file was created and has content
        if [ -s "$output_file" ]; then
            echo "  ✓ Saved: $output_file"
        else
            echo "  ✗ Failed to generate TTS for $current_book $current_chapter:$current_verse"
            rm -f "$output_file"
        fi

        # Rate limiting - small delay
        sleep 0.5
    fi

    # Update progress
    new_completed=$((6216 + generated_count + 1))
    update_progress "$current_book" "$current_chapter" "$current_verse" "$new_completed"

    # Increment counters
    generated_count=$((generated_count + 1))

    # Move to next verse
    current_verse=$((current_verse + 1))

    # Check if we need to move to next chapter
    chapter_verse_count=$(get_verse_count "$current_book" "$current_chapter")
    if [ $current_verse -gt $chapter_verse_count ]; then
        echo "Chapter $current_book $current_chapter complete. Moving to next chapter."
        current_chapter=$((current_chapter + 1))
        current_verse=1

        # Check if we need to move to next book (Joshua has 24 chapters)
        if [ "$current_book" = "joshua" ] && [ $current_chapter -gt 24 ]; then
            echo "Book Joshua complete. Task ended."
            break
        fi
    fi

    # Report progress every 25 verses
    if [ $((generated_count % 25)) -eq 0 ]; then
        echo "=== PROGRESS REPORT ==="
        echo "Verses generated: $generated_count/$TARGET_COUNT"
        echo "Current position: $current_book $current_chapter:$current_verse"
        echo "Total progress: $new_completed/31,417 verses"
        percentage=$(echo "scale=2; $new_completed * 100 / 31417" | bc)
        echo "Percentage: $percentage%"
        echo "======================="
    fi
done

# Final update
echo ""
echo "=== TASK COMPLETE ==="
echo "Verses generated: $generated_count"
echo "Final position: $current_book $current_chapter:$current_verse"
final_completed=$((6216 + generated_count))
echo "Total completed: $final_completed"
percentage=$(echo "scale=2; $final_completed * 100 / 31417" | bc)
echo "Total progress: $percentage%"

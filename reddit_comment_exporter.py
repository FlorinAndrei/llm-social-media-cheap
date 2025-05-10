import praw
import csv
import os
import time
import argparse
from datetime import datetime
import sys
import re


def clean_text(text):
    """Clean text to remove control characters but preserve newlines and formatting"""
    if not text:
        return ""
    # Remove control characters except newlines and carriage returns
    text = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]', '', text)
    return text


def get_parent_text(reddit_instance, parent_id):
    """
    Get the text of the parent (either comment body or submission title+selftext)
    Returns None if parent is missing or deleted

    Args:
        reddit_instance: Authenticated PRAW Reddit instance
        parent_id: The ID of the parent (comment or submission)
    """
    try:
        # If parent_id doesn't have a prefix, we need to determine if it's a comment or submission
        if not parent_id.startswith('t1_') and not parent_id.startswith('t3_'):
            # Try to fetch as comment first
            try:
                parent = reddit_instance.comment(id=parent_id)
                parent.body  # This will trigger a request to Reddit
                parent_id = f"t1_{parent_id}"
            except:
                # If that fails, try as submission
                try:
                    parent = reddit_instance.submission(id=parent_id)
                    parent.title  # This will trigger a request to Reddit
                    parent_id = f"t3_{parent_id}"
                except:
                    print(f"Could not determine type of parent with ID {parent_id}")
                    return None

        # Now fetch the parent with the proper prefix
        if parent_id.startswith('t1_'):
            parent = reddit_instance.comment(id=parent_id[3:])
            body = clean_text(parent.body)
            # Skip if parent is deleted
            if body == "[deleted]" or body == "[removed]":
                return None
            return body
        elif parent_id.startswith('t3_'):
            parent = reddit_instance.submission(id=parent_id[3:])
            title = clean_text(parent.title)
            selftext = clean_text(parent.selftext) if parent.selftext else ""

            # Skip if submission appears to be deleted (check both title and selftext)
            if title == "[deleted]" or title == "[removed]" or selftext == "[deleted]" or selftext == "[removed]":
                print(f"Skipping comment with deleted parent submission. Title: '{title}', Selftext: '{selftext}'")
                return None

            if selftext:
                # Preserve the newline between title and selftext
                return f"{title}\n{selftext}"
            else:
                return title

        return None  # Unknown parent type
    except Exception as e:
        print(f"Error getting parent text for parent ID {parent_id}: {e}")
        return None  # Parent is missing or inaccessible


def process_comments_from_csv(
    reddit_instance, input_file, output_file, batch_size=100, max_retries=3, retry_delay=60, stop_after=None
):
    """
    Process comments from a CSV file, fetch their parents, and export to a new CSV file.

    Args:
        reddit_instance: Authenticated PRAW Reddit instance
        input_file: Path to the input CSV file containing comments
        output_file: Path to the CSV output file
        batch_size: Number of comments to process before saving progress
        max_retries: Maximum number of retries for API errors
        retry_delay: Delay in seconds between retries
        stop_after: Maximum number of comments to process (None for all)
    """
    # Check if the output file exists and get the last processed comment ID
    last_comment_id = None
    if os.path.exists(output_file) and os.path.getsize(output_file) > 0:
        try:
            with open(output_file, 'r', encoding='utf-8', errors='replace') as f:
                reader = csv.reader(f)
                # Skip header if it exists
                next(reader, None)
                # Read all lines and keep track of the last valid comment ID
                for row in reader:
                    if len(row) >= 2:
                        last_comment_id = row[1]
                if last_comment_id:
                    print(f"Resuming from comment ID: {last_comment_id}")
        except Exception as e:
            print(f"Error reading existing file: {e}")
            print("Starting from the beginning.")

    # Open the file in append mode if it exists, otherwise create it
    file_exists = os.path.exists(output_file) and os.path.getsize(output_file) > 0

    with open(output_file, 'a' if file_exists else 'w', newline='', encoding='utf-8') as out_f:
        writer = csv.writer(out_f, quoting=csv.QUOTE_ALL)

        # Write header if the file is new
        if not file_exists:
            writer.writerow(['timestamp', 'comment_id', 'comment_body', 'parent_text'])

        # Flag to track if we've found the last processed comment
        found_last_comment = last_comment_id is None

        # Counters for processed comments
        processed_count = 0
        skipped_count = 0
        total_count = 0
        start_time = time.time()

        try:
            with open(input_file, 'r', encoding='utf-8', errors='replace') as in_f:
                reader = csv.DictReader(in_f)

                for row in reader:
                    total_count += 1
                    comment_id = row.get('id')

                    # Skip if we haven't found the last processed comment yet
                    if not found_last_comment:
                        if comment_id == last_comment_id:
                            found_last_comment = True
                            print(f"Found last processed comment (ID: {last_comment_id})")
                        continue

                    # Skip if we've reached the stop_after limit
                    if stop_after is not None and processed_count >= stop_after:
                        print(f"Reached stop-after limit of {stop_after} comments")
                        break

                    # Get parent ID - either from "parent" field or extracted from "link" field
                    parent_id = row.get('parent')

                    # If parent ID is missing, try to extract from link
                    if not parent_id:
                        link = row.get('link')
                        if link:
                            try:
                                # Extract the second field from the right in the URL
                                # Remove trailing slash if present
                                link = link.rstrip('/')
                                # Split by '/' and get the second to last element
                                parts = link.split('/')
                                if len(parts) >= 2:
                                    parent_id = parts[-2]
                            except Exception as e:
                                print(f"Error extracting parent ID from link {link}: {e}")

                    # Skip if parent ID is still missing
                    if not parent_id:
                        skipped_count += 1
                        if skipped_count % 10 == 0:
                            print(
                                f"Skipped {skipped_count} comments with missing parent IDs (Total seen: {total_count})"
                            )
                        continue

                    retry_count = 0
                    while retry_count < max_retries:
                        try:
                            # Get the parent text
                            parent_text = get_parent_text(reddit_instance, parent_id)

                            # Skip if parent is missing or deleted
                            if parent_text is None:
                                skipped_count += 1
                                if skipped_count % 10 == 0:
                                    print(
                                        f"Skipped {skipped_count} comments with missing/deleted parents (Total seen: {total_count})"
                                    )
                                break

                            # Get the timestamp
                            timestamp = row.get('date', '')

                            # Get the comment body and clean it
                            comment_body = clean_text(row.get('body', ''))

                            # Write to CSV
                            writer.writerow([timestamp, comment_id, comment_body, parent_text])

                            processed_count += 1

                            # Flush to disk and report progress every batch_size comments
                            if processed_count % batch_size == 0:
                                out_f.flush()
                                os.fsync(out_f.fileno())
                                elapsed_time = time.time() - start_time
                                rate = processed_count / elapsed_time if elapsed_time > 0 else 0
                                print(
                                    f"Processed {processed_count} comments (Total seen: {total_count}, Skipped: {skipped_count}, Rate: {rate:.2f} comments/sec)"
                                )

                            # Break out of retry loop on success
                            break

                        except praw.exceptions.PRAWException as e:
                            retry_count += 1
                            if retry_count >= max_retries:
                                print(f"Failed to process comment after {max_retries} retries: {e}")
                                skipped_count += 1
                                break
                            print(
                                f"Reddit API error: {e}. Retrying in {retry_delay} seconds... ({retry_count}/{max_retries})"
                            )
                            time.sleep(retry_delay)
                        except Exception as e:
                            print(f"Error processing comment {comment_id}: {e}")
                            skipped_count += 1
                            break

        except KeyboardInterrupt:
            print("\nInterrupted by user. Progress has been saved.")
        except Exception as e:
            print(f"Error: {e}")
        finally:
            elapsed_time = time.time() - start_time
            rate = processed_count / elapsed_time if elapsed_time > 0 else 0
            print(
                f"Completed. Processed {processed_count} comments, skipped {skipped_count} with missing/deleted parents "
                f"(Total seen: {total_count}) in {elapsed_time:.2f} seconds ({rate:.2f} comments/sec)."
            )


def parse_arguments():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description='Export Reddit comments to CSV')
    parser.add_argument('--username', type=str, help='Reddit username to fetch comments for')
    parser.add_argument(
        '--input', type=str, default="comments.csv", help='Path to the input CSV file containing comments'
    )
    parser.add_argument('--output', type=str, default="conversations.csv", help='Path to the CSV output file')
    parser.add_argument(
        '--batch-size', type=int, default=100, help='Number of comments to process before saving progress'
    )
    parser.add_argument('--max-retries', type=int, default=3, help='Maximum number of retries for API errors')
    parser.add_argument('--retry-delay', type=int, default=60, help='Delay in seconds between retries')
    parser.add_argument('--stop-after', type=int, help='Maximum number of comments to process')
    return parser.parse_args()


if __name__ == "__main__":
    # Parse command line arguments
    args = parse_arguments()

    # Reddit API credentials
    # You can also use environment variables for these
    client_id = os.environ.get("REDDIT_CLIENT_ID")
    client_secret = os.environ.get("REDDIT_CLIENT_SECRET")
    password = os.environ.get("REDDIT_PASSWORD")
    username = os.environ.get("REDDIT_USERNAME")
    user_agent = os.environ.get("REDDIT_USER_AGENT")

    try:
        # Initialize Reddit API
        reddit = praw.Reddit(
            client_id=client_id,
            client_secret=client_secret,
            password=password,
            user_agent=user_agent,
            username=username,
        )

        # Verify authentication
        print(f"Authenticated as: {reddit.user.me()}")

        # Process comments from CSV file
        process_comments_from_csv(
            reddit,
            args.input,
            args.output,
            batch_size=args.batch_size,
            max_retries=args.max_retries,
            retry_delay=args.retry_delay,
            stop_after=args.stop_after,
        )
    except Exception as e:
        print(f"Error initializing Reddit API: {e}")
        sys.exit(1)

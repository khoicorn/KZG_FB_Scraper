"""
Card components for domain processing interface.
Easy to import and use in other files.
"""
from lark_bot import DATE_NOW

def domain_processing_card(search_word, progress_percent=0):
    """
    Creates a processing card with progress bar.
    
    Args:
        search_word (str): The domain being processed
        timestamp (str): Current timestamp
        progress_percent (int): Progress percentage (0-100)
    
    Returns:
        dict: Card configuration
    """
    filled_blocks = int(progress_percent / 20)
    empty_blocks = 5 - filled_blocks
    progress_bar = "🟩" * filled_blocks + "⬜" * empty_blocks

    return {
        "elements": [
            {
                "tag": "column_set",
                "flex_mode": "none",
                "columns": [
                    {
                        "tag": "column",
                        "width": "weighted",
                        "weight": 1,
                        "elements": [{
                            "tag": "div",
                            "text": {
                                "content": f"**🎯 Domain**\n{search_word}",
                                "tag": "lark_md"
                            }
                        }]
                    },
                    {
                        "tag": "column",
                        "width": "weighted",
                        "weight": 1,
                        "elements": [{
                            "tag": "div",
                            "text": {
                                "content": f"**🕒 Time**\n{DATE_NOW}",
                                "tag": "lark_md"
                            }
                        }]
                    }
                ]
            },
            {
                "tag": "div",
                "text": {
                    "content": f"**Progress:** {progress_bar} {progress_percent}%",
                    "tag": "lark_md"
                }
            },
            {
                "tag": "hr"
            },
            {
                "tag": "div",
                "text": {
                    "content": "💡 Type '/cancel' anytime to stop the process",
                    "tag": "lark_md"
                }
            }
        ],
        "header": {
            "template": "indigo",
            "title": {
                "content": "🔍 Processing request... This may take a minute",
                "tag": "plain_text"
            }
        }
    }


def search_complete_card(search_word, num_results):
    """
    Creates a completion card showing successful search results.
    
    Args:
        search_word (str): The domain that was searched
        timestamp (str): Completion timestamp
        num_results (int): Number of results found
    
    Returns:
        dict: Card configuration
    """
    return {
        "elements": [
            {
                "tag": "column_set",
                "flex_mode": "none",
                "background_style": "default",
                "columns": [
                    {
                        "tag": "column",
                        "width": "weighted",
                        "weight": 1,
                        "vertical_align": "top",
                        "elements": [
                            {
                                "tag": "div",
                                "text": {
                                    "content": f"**🎯 Domain**\n{search_word}",
                                    "tag": "lark_md"
                                }
                            }
                        ]
                    },
                    {
                        "tag": "column",
                        "width": "weighted",
                        "weight": 1,
                        "vertical_align": "top",
                        "elements": [
                            {
                                "tag": "div",
                                "text": {
                                    "content": f"**🕐 Time:**\n{DATE_NOW}",
                                    "tag": "lark_md"
                                }
                            }
                        ]
                    }
                ]
            },
            {
                "tag": "column_set",
                "flex_mode": "none",
                "background_style": "default",
                "columns": []
            },
            {
                "tag": "div",
                "text": {
                    "content": f"**Search completed:** {num_results} results found",
                    "tag": "lark_md"
                }
            }
        ],
        "header": {
            "template": "green",
            "title": {
                "content": "✅ Complete",
                "tag": "plain_text"
            }
        }
    }


def search_no_result_card(search_word, href):
    """
    Creates a card for when no search results are found.
    
    Args:
        search_word (str): The domain that was searched
        timestamp (str): Search completion timestamp
        href (str): URL link for manual checking
    
    Returns:
        dict: Card configuration
    """
    return {
        "elements": [
            {
                "tag": "column_set",
                "flex_mode": "none",
                "background_style": "default",
                "columns": [
                    {
                        "tag": "column",
                        "width": "weighted",
                        "weight": 1,
                        "vertical_align": "top",
                        "elements": [
                            {
                                "tag": "div",
                                "text": {
                                    "content": f"**🎯 Domain**\n{search_word}",
                                    "tag": "lark_md"
                                }
                            }
                        ]
                    },
                    {
                        "tag": "column",
                        "width": "weighted",
                        "weight": 1,
                        "vertical_align": "top",
                        "elements": [
                            {
                                "tag": "div",
                                "text": {
                                    "content": f"**🕐 Time:**\n{DATE_NOW}",
                                    "tag": "lark_md"
                                }
                            }
                        ]
                    }
                ]
            },
            {
                "tag": "column_set",
                "flex_mode": "none",
                "background_style": "default",
                "columns": []
            },
            {
                "tag": "div",
                "text": {
                    "content": f"**No result found:** [Click here to check]({href})",
                    "tag": "lark_md"
                }
            }
        ],
        "header": {
            "template": "gray",
            "title": {
                "content": "📭 No result found",
                "tag": "plain_text"
            }
        }
    }


def queue_card(search_word, position):
    """
    Creates a queue waiting card.
    
    Args:
        search_word (str): The domain waiting to be processed
        timestamp (str): Queue entry timestamp
        position (int): Position in queue
    
    Returns:
        dict: Card configuration
    """
    return {
        "elements": [
            {
                "tag": "column_set",
                "flex_mode": "none",
                "background_style": "default",
                "columns": [
                    {
                        "tag": "column",
                        "width": "weighted",
                        "weight": 1,
                        "vertical_align": "top",
                        "elements": [
                            {
                                "tag": "div",
                                "text": {
                                    "content": f"**🎯 Domain**\n{search_word}",
                                    "tag": "lark_md"
                                }
                            }
                        ]
                    },
                    {
                        "tag": "column",
                        "width": "weighted",
                        "weight": 1,
                        "vertical_align": "top",
                        "elements": [
                            {
                                "tag": "div",
                                "text": {
                                    "content": f"**🕐 Time:**\n{DATE_NOW}",
                                    "tag": "lark_md"
                                }
                            }
                        ]
                    }
                ]
            },
            {
                "tag": "column_set",
                "flex_mode": "none",
                "background_style": "default",
                "columns": []
            },
            {
                "tag": "div",
                "text": {
                    "content": f"📍 Current position in queue: **#{position}**. I'll ping you when it starts.",
                    "tag": "lark_md"
                }
            },
            {
                "tag": "hr"
            },
            {
                "tag": "div",
                "text": {
                    "content": "💡 Type '/cancel' anytime to stop the process",
                    "tag": "lark_md"
                }
            }
        ],
        "header": {
            "template": "yellow",
            "title": {
                "content": "⏳ You are waiting in a queue",
                "tag": "plain_text"
            }
        }
    }


# Convenience function to get all available cards
def get_available_cards():
    """
    Returns a list of all available card functions.
    
    Returns:
        list: Available card function names
    """
    return [
        'domain_processing_card',
        'search_complete_card', 
        'search_no_result_card',
        'queue_card'
    ]


# Example usage
# if __name__ == "__main__":
#     from datetime import datetime
    
#     # Example usage of each card
#     timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
#     # Processing card
#     processing = domain_processing_card("example.com", timestamp, 50)
#     print("Processing card created")
    
#     # Complete card  
#     complete = search_complete_card("example.com", timestamp, 25)
#     print("Complete card created")
    
#     # No results card
#     no_results = search_no_result_card("example.com", timestamp, "https://example.com")
#     print("No results card created")
    
#     # Queue card
#     queue = queue_card("example.com", timestamp, 3)
#     print("Queue card created")
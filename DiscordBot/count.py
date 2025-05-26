harassment_counts = {}

def increment_harassment_count(guild_id: int, user_id: int):
    # Increment the harassment count for a specific user within a guild
    if guild_id not in harassment_counts:
        harassment_counts[guild_id] = {}
    guild_counts = harassment_counts[guild_id]
    guild_counts[user_id] = guild_counts.get(user_id, 0) + 1

def get_counts(guild_id: int):
    # Return a dict mapping user_id to harassment count for the given guild
    return harassment_counts.get(guild_id, {})


# Example

# harassment_counts = {
#      guild/server ID
#     111111111111111111: { 
#         offender ID
#         285349080926183426: 4,
#         492038475029384720: 1,
#         130987650948372641: 7
# }
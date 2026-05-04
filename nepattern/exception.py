class MatchFailed(Exception):
    """pattern match failed"""


class UserMatchFailed(MatchFailed):
    """pattern match failed caused by user's custom converter"""

def get_user_profile(service):
    """
    Fetches the profile of the authenticated user.
    Returns the email address.
    """
    try:
        profile = service.users().getProfile(userId='me').execute()
        return profile.get("emailAddress")
    except Exception as e:
        print(f"Error fetching user profile: {e}")
        return None

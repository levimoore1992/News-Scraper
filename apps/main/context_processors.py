def notifications(request):
    """A context processor that provides the user's notifications to all templates."""
    if request.user.is_authenticated:
        return {"notifications": request.user.notifications.filter(is_read=False)}
    return {}

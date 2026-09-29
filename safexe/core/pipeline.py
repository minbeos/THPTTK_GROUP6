def populate_user_fields(strategy, details, backend, user=None, *args, **kwargs):
    if user:
        if not user.full_name and details.get('fullname'):
            user.full_name = details['fullname']
        user.save()

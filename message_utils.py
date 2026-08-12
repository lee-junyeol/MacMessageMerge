def merge_message(template: str, recipient: dict) -> str:
    values = {
        'name': str(recipient.get('name', '') or ''),
        'phone': str(recipient.get('phone', '') or ''),
    }
    result = template
    for key, value in values.items():
        result = result.replace('{' + key + '}', value)
    return result

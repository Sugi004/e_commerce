from datetime import datetime

def validate_and_convert_dates(data, fields):
    """
    Ensure that specified datetime fields are ISO 8601 strings.
    
    Args:
        data (dict): The dictionary containing the fields to validate.
        fields (list): A list of field names to validate and convert.

    Returns:
        dict: The updated dictionary with datetime fields in ISO format.
    """
    for field in fields:
        if field in data:
            value = data[field]
            if isinstance(value, datetime):
                data[field] = value.isoformat()
            elif isinstance(value, str):
                try:
                    # Validate the string can be parsed
                    datetime.fromisoformat(value)
                except ValueError:
                    raise ValueError(f"Invalid ISO datetime string for field '{field}': {value}")
            else:
                raise ValueError(f"Field '{field}' must be a datetime object or ISO 8601 string.")
    return data

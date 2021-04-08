"""A collection of functions to assist with parsing client errors returned from the boto3 library."""
# Third party imports
import botocore


# *** client_error_is_instance **********************************************

def client_error_is_instance(exception: botocore.exceptions.ClientError, exception_type: str) -> bool:
    """Return True if the given exception has the provided type.

    Args:
        exception (botocore.exceptions.ClientError): The client exception thrown by the boto3 library.
        exception_type (str): The desired type of the exception.

    Returns:
        bool: Whether the provided exception matches the provided type.
    """
    return "Error" in exception.response and "Code" in exception.response["Error"] and exception.response["Error"]["Code"] == exception_type

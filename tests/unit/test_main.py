from unittest.mock import MagicMock, Mock, patch

# Import the functions we want to test
from netbox_pdns.__main__ import main, parse_args


def test_default_args() -> None:
    """Test that default arguments are set correctly."""
    # Mock sys.argv to simulate no command line arguments
    with patch("sys.argv", ["__main__.py"]):
        args = parse_args()
        assert args.host == "127.0.0.1"
        assert args.port == 8000


def test_custom_host() -> None:
    """Test setting a custom host."""
    with patch("sys.argv", ["__main__.py", "--host", "0.0.0.0"]):
        args = parse_args()
        assert args.host == "0.0.0.0"
        assert args.port == 8000


def test_custom_port() -> None:
    """Test setting a custom port."""
    with patch("sys.argv", ["__main__.py", "--port", "9000"]):
        args = parse_args()
        assert args.host == "127.0.0.1"
        assert args.port == 9000


def test_custom_host_and_port() -> None:
    """Test setting both custom host and port."""
    with patch("sys.argv", ["__main__.py", "--host", "localhost", "--port", "8080"]):
        args = parse_args()
        assert args.host == "localhost"
        assert args.port == 8080


@patch("netbox_pdns.__main__.create_app")
@patch("netbox_pdns.__main__.Settings")
@patch("netbox_pdns.__main__.uvicorn.run")
def test_main_default_args(mock_run: Mock, mock_settings: Mock, mock_create_app: Mock) -> None:
    """Test that main function calls uvicorn.run with default arguments."""
    # Set up mocks
    mock_app = MagicMock()
    mock_create_app.return_value = mock_app
    mock_settings_instance = MagicMock()
    mock_settings_instance.log_level = "INFO"
    mock_settings.return_value = mock_settings_instance

    # Mock command line arguments
    with patch("sys.argv", ["__main__.py"]):
        main()

    # Verify uvicorn.run was called with correct arguments
    mock_run.assert_called_once_with(mock_app, host="127.0.0.1", port=8000, log_level="info")


@patch("netbox_pdns.__main__.create_app")
@patch("netbox_pdns.__main__.Settings")
@patch("netbox_pdns.__main__.uvicorn.run")
def test_main_custom_args(mock_run: Mock, mock_settings: Mock, mock_create_app: Mock) -> None:
    """Test that main function calls uvicorn.run with custom arguments."""
    # Set up mocks
    mock_app = MagicMock()
    mock_create_app.return_value = mock_app
    mock_settings_instance = MagicMock()
    mock_settings_instance.log_level = "DEBUG"
    mock_settings.return_value = mock_settings_instance

    # Mock command line arguments
    with patch("sys.argv", ["__main__.py", "--host", "0.0.0.0", "--port", "9000"]):
        main()

    # Verify uvicorn.run was called with correct arguments
    mock_run.assert_called_once_with(mock_app, host="0.0.0.0", port=9000, log_level="debug")

import pytest
from unittest.mock import patch
from streamlit.testing.v1 import AppTest

# Since we are testing app.py which uses relative/absolute paths or dependencies,
# we ensure we can test the UI elements.

@pytest.fixture
def app():
    # Initialize the Streamlit app test
    # The path is relative to where pytest is run, we assume it's run from the frontend folder
    return AppTest.from_file("app.py").run()

def test_app_renders_successfully(app):
    """Test that the app renders the title and basic layout without errors."""
    assert not app.exception
    # Check title
    assert app.title[0].value == "📅 Daily Attention Agent (DAA)"
    
    # Check sidebar inputs
    assert app.sidebar.text_input[0].label == "User ID"
    assert app.sidebar.text_input[1].label == "Workspace ID"
    assert app.sidebar.text_area[0].label == "VIP Senders (comma separated)"
    assert app.sidebar.text_area[1].label == "Keywords (comma separated)"

@patch('requests.post')
@patch('requests.get')
def test_successful_run_flow(mock_get, mock_post):
    """Test the UI when pushing the run agent button and getting a successful response."""
    # Mocking the POST request to start the run
    mock_post.return_value.status_code = 200
    mock_post.return_value.json.return_value = {"run_id": "test_run_123"}
    
    # Mocking the GET request for status polling
    mock_get.return_value.status_code = 200
    mock_get.return_value.json.return_value = {
        "status": "success",
        "result": {
            "attention_items": [
                {"title": "Important Email", "priority_score": 90, "summary": "Needs your attention"}
            ],
            "risks": [
                {"title": "Project Delay", "reason": "Missing resources"}
            ],
            "opportunities": [
                {"title": "Upsell", "suggestion": "Offer premium support"}
            ]
        }
    }
    
    # Run the app
    app = AppTest.from_file("app.py").run()
    
    # Click the primary button
    app.button[0].click().run()
    
    # Assert no exceptions occurred during execution
    assert not app.exception
    
    # Verify success messaging after polling
    assert "Run started successfully!" in app.success[0].value
    assert "test_run_123" in app.success[0].value
    
    # Fetch specific headers by filtering or counting correctly
    subheaders = [h.value for h in app.subheader]
    
    assert "🔥 Attention Items" in subheaders
    assert "Important Email" in app.markdown[1].value
    
    assert "⚠️ Risks Identified" in subheaders
    assert app.warning[0].value == "- **Project Delay**: Missing resources"
    
    assert "💡 Opportunities" in subheaders
    assert app.info[1].value == "- **Upsell**: Offer premium support"

@patch('requests.post')
def test_failed_run_flow(mock_post):
    """Test the UI handles a failure from the Gateway properly."""
    # Mock a server failure
    mock_post.return_value.status_code = 500
    mock_post.return_value.json.return_value = {"detail": "Internal Server Error"}
    # requests.raise_for_status() usually throws HTTPError, but Streamlit should handle or bubble it.
    import requests
    mock_post.return_value.raise_for_status.side_effect = requests.exceptions.HTTPError("500 Server Error")
    
    app = AppTest.from_file("app.py").run()
    
    # Click the run button
    app.button[0].click().run()
    
    # Streamlit may handle the exception and display it.
    assert len(app.exception) > 0 or len(app.error) > 0
    if len(app.exception) > 0:
        assert "500 Server Error" in str(app.exception[0])
    else:
        assert "500 Server Error" in str(app.error[0].value)

import os
import tempfile
import pytest

from assignment import main

@pytest.fixture
def client():
    db_fd, main.app.config['DATABASE'] = tempfile.mkstemp()
    main.app.config['TESTING'] = True
    client = main.app.test_client()

    with main.app.app_context():
        main.init_db()

        
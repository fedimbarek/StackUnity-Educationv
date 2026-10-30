import os
import sys
import threading
import time
import unittest
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import store


class StoreConcurrencyTests(unittest.TestCase):
    def test_sparql_calls_are_serialized_on_the_shared_graph(self):
        graph_query = store.onto.query
        active_queries = 0
        maximum_active_queries = 0
        state_lock = threading.Lock()

        def tracked_query(*args, **kwargs):
            nonlocal active_queries, maximum_active_queries
            with state_lock:
                active_queries += 1
                maximum_active_queries = max(maximum_active_queries, active_queries)
            try:
                time.sleep(0.01)
                return graph_query(*args, **kwargs)
            finally:
                with state_lock:
                    active_queries -= 1

        def run_query(_):
            return store.sparql("SELECT ?value WHERE { BIND(1 AS ?value) }")

        with patch.object(store.onto, "query", side_effect=tracked_query):
            with ThreadPoolExecutor(max_workers=8) as executor:
                results = list(executor.map(run_query, range(16)))

        self.assertEqual(len(results), 16)
        self.assertTrue(all(result == [{"value": "1"}] for result in results))
        self.assertEqual(maximum_active_queries, 1)


if __name__ == "__main__":
    unittest.main()

import unittest
import uuid

import app as smartfin


class SmartFinSmokeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        smartfin.app.config.update(TESTING=True, SECRET_KEY="test-secret-key")
        smartfin.initialize()
        smartfin.seed()

    def setUp(self):
        self.client = smartfin.app.test_client()

    def test_workspace_redirects_to_login(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 302)
        self.assertIn("/login", response.headers["Location"])

    def test_signup_and_signout(self):
        unique = uuid.uuid4().hex[:10]
        response = self.client.post("/signup", data={
            "full_name": "Test User",
            "email": f"test-{unique}@example.com",
            "password": "SafeTestPassword123",
            "confirm_password": "SafeTestPassword123",
        }, follow_redirects=False)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(self.client.get("/").status_code, 200)
        self.assertEqual(self.client.get("/company-analysis").status_code, 200)
        response = self.client.post("/logout", follow_redirects=False)
        self.assertEqual(response.status_code, 302)
        self.assertIn("/login", response.headers["Location"])

    def test_company_analysis_page_requires_session(self):
        response = self.client.get("/company-analysis")
        self.assertEqual(response.status_code, 302)
        self.assertIn("/login", response.headers["Location"])


    def test_same_company_year_can_store_both_statement_scopes(self):
        unique = uuid.uuid4().hex[:10]
        company = f"Scope Test {unique}"
        self.client.post("/signup", data={
            "full_name": "Scope Tester",
            "email": f"scope-{unique}@example.com",
            "password": "SafeTestPassword123",
            "confirm_password": "SafeTestPassword123",
        })
        for scope in ("STANDALONE", "CONSOLIDATED"):
            response = self.client.post("/company-analysis/save", data={
                "company_name": company,
                "fiscal_year": "FY2026",
                "statement_scope": scope,
                "source_filename": "test.pdf",
                "unit": "INR crore",
                "CURRENT_ASSETS": "100",
                "CURRENT_LIABILITIES": "50",
                "INVENTORY": "10",
            })
            self.assertEqual(response.status_code, 302)
        count = smartfin.query(
            """SELECT COUNT(*) AS n FROM financial_periods p
               JOIN companies c USING(company_id)
               WHERE c.company_name=? AND p.fiscal_year=?""",
            (company, "FY2026"),
        )[0]["n"]
        self.assertEqual(count, 2)


if __name__ == "__main__":
    unittest.main()

# Source onboarding checklist

Before adding a source, confirm:

1. The source is approved for the business purpose.
2. Its terms, robots policy and authentication constraints are understood.
3. An API, feed or newsletter route has been considered before browser automation.
4. Expected fields and example records are available.
5. Normal result volume and update frequency are known.
6. Rate limits and backoff rules are defined.
7. A change or zero-result condition will fail loudly.
8. The source has an owner and a manual fallback.
9. Test fixtures contain no private credentials or personal data.
10. Acceptance checks cover pagination, duplicates, deadlines and malformed pages.

Logged-in social platforms and search engines should not be automated unless an approved API or explicit permission supports the intended use.


"""
Analytics holds no models of its own. Project context Section 1 flagged
Analytics as "meaningless without data from the core loop existing first" —
now that the core loop (Customers/Leads/Projects/Invoices) exists, this app
is purely a read/aggregation layer over that data (see services.py), not a
new source of truth. If saved/scheduled reports become a requirement later,
that's a real model (SavedReport) added here at that point — not
speculatively added now.
"""

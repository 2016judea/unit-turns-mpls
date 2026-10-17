# Data model — written before looking at the data (BUSINESS.md rule 5)

**The buyer:** a painter, cleaner or turnover crew who does unit turns for property
managers (Tom Harer: *"I partner with property management groups to complete their unit
turns"*; a St. Paul crew: *"Are slow unit turnovers costing you rental income?"*).
**The question:** which managers turn the most units near me, and how do I reach them?

## Ideal model

**Manager** (the firm that hires the turn crew)
| field | answers |
|---|---|
| firm name | who to ask for |
| contact: person, phone, email | how to reach the one who books vendors |
| units managed | how much turn work they generate (rank) |
| buildings (list) | where the work is, and how far from me |
| move-outs per month / vacancy | how many turns are coming, when |
| current turnover vendor | who I'd be displacing |

**Building**
| field | answers |
|---|---|
| address, lat/lon | where; distance from me |
| units | size of the job pool |
| owner of record | who pays, if the manager won't answer |
| manager (FK) | who books the work |
| licence condition tier | buildings with problems need more work |
| recent sale: month, price, new owner | a new owner turns and repaints units |

## Reality check (2026-10-17)

| field | source | filled? |
|---|---|---|
| firm, contact person, phone, email | Minneapolis Active Rental Licenses (applicant = the manager the city contacts; email domain = the firm) | **yes, Minneapolis.** St. Paul: **no**, its Certificate of Occupancy register names no manager or contact |
| units, address, lat/lon | Minneapolis rental licenses; St. Paul C of O (3+ units, frozen 2025-07-01) | yes |
| owner of record | Minneapolis licence owner field; Ramsey parcels for St. Paul | yes |
| licence tier | Minneapolis licence tier (1–3) | yes, Minneapolis |
| recent sale + new owner | Hennepin / Ramsey parcel sale month + price + current owner (snapshot through mid-2026) | yes, month grain only |
| move-outs / vacancy | no public record | **no** |
| current turnover vendor | no public record | **no** |

**Call:** build. Units stand in for turn volume (turnover runs roughly proportional to
units), which is the ranking the posts ask for. The two unfillable fields are named on the
page. St. Paul ships as owner-of-record only and says so, because the city publishes no
manager.

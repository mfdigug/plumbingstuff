# Product search — manual test queries

Updated 12 Aug 2026, post filler-word and unstocked-brand fixes (see
`docs/real-backend-contract.md`). For manual QA against the 11labs voice
agent once it's wired up to this mock's `/api/v1/product-search`.

## A. Clean matches — expect status "matched", high confidence, correct product

1. "I need a roll of PTFE tape"
   Expect: matched — Atomik PTFE Thread Tape

2. "Can I get a length of Auspex pipe"
   Expect: matched — Auspex Pipe PEX 100 16mm x 50mtr

3. "I need a Dura mini stop valve"
   Expect: matched — Dura Std Mini Stop CP 15mm LF

4. "Need a Caroma toilet seat"
   Expect: matched — Caroma Titan Toilet Seat. Note: the shortlist behind it
   also contains three Toilet Roll Holders, all also labeled "high"
   confidence — a real quirk worth checking the agent doesn't get confused
   by (see item M below).

## B. Brand-mishearing slang — expect status "matched", correctly resolves what the customer actually meant

5. "I need three half inch ozpex elbows"
   Expect: matched — Auspex LF MI Lug Elbow 16mm, rationale references "ozpex"

6. "Got any popper press couplings"
   Expect: matched — a Copper Press Coupling product

7. "Any speed deck clips for the roof"
   Expect: matched — Apex Roof Clip, Speed Deck profile

8. "Need some wolfrate for the frame"
   Expect: matched — All Thread Rod, rationale references "wolfrate"

## C. Needs checking — expect status "needs_checking", agent should confirm before adding

9. "Need a york flex connector"
   Expect: needs_checking, medium confidence — resolves to a DWV/PEX
   coupling, but not confidently enough to skip a question

10. "Got any thermal wrap for pipes"
    Expect: needs_checking, medium confidence — Solar Armor Flex Pipe Lagging

11. "Need a fitting for the shower, the round bit water comes out of"
    Expect: needs_checking, medium confidence — Meir Shower Rose

## D. Unstocked brand — customer names a real brand this store doesn't carry

12. "Need a jaeger fitting"
    Expect: needs_checking. Rationale should explicitly say Jaeger isn't
    stocked and name the substitute product.

13. "Need a chem press elbow"
    Expect: needs_checking. Rationale should explicitly say Chem Press
    isn't stocked and name the substitute product.

## E. No match — expect status "not_found", empty products list, still a normal (200) response

14. "Need a xylophone"
    Expect: not_found

15. "Got any violin strings"
    Expect: not_found (this one used to falsely match "Adjustable Cap and
    Lining" before a fix earlier today — good regression check)

16. "Need a bag of quikrete"
    Expect: not_found (this one used to falsely match a "Towel Rail" before
    the same fix — also a good regression check)

## F. Multi-item — one utterance, multiple independently-statused results

17. "I need a 90mm stormwater flex and a roll of PTFE tape"
    Expect: two items. PTFE tape matches cleanly. The stormwater flex
    currently mismatches to "Solar Armor Flex Pipe Lagging" (a real
    semantic-confusion bug — "flex" is overloaded between a flexible
    coupling and the "Armor Flex" insulation brand name). Good one to keep
    testing as-is.

18. "Three half inch ozpex elbows and two flanged lock nuts"
    Expect: two items, both matched correctly.

19. "Need a rose for the shower and a new toilet roll holder"
    Expect: two items, both matched, correctly disambiguated by surrounding
    context even though "rose" alone is ambiguous.

## G. Ambiguous single words — currently resolve to "matched" rather than asking a question (worth knowing, since it means the mock is more confident than a real customer conversation probably warrants)

20. "Need an elbow"
21. "Need a tap"
22. "Need a coupling"
23. "Need a unit"
24. "Can I get a length of PVC pressure pipe"

Expect for all of the above: matched, high confidence, but the choice of
exactly which product wins is arguably arbitrary — worth sanity-checking
each one's specific top pick rather than assuming it asked a clarifying
question.

## H. Multi-turn correction flow (manual, two utterances)

25. Turn 1: "Need a Caroma toilet seat" — agent should read back the toilet
    seat.
    Turn 2: "No, I meant the roll holder" — check whether the agent finds
    the Toilet Roll Holder already sitting in the first response's
    products/alternates lists rather than re-querying. It should be there
    already (same brand, retrieved in the original response).

# Sample policy updates

Files for trying PolicyPal's policy-update feature (admin page at `/admin`, or the API described in the main README).

| File | What it does | Question to ask afterwards |
|---|---|---|
| `POL-13_parking_policy.md` | **Adds** a new policy (POL-13) | "How many parking spaces are at headquarters?" → 120, cited to POL-13 |
| `POL-14_pets_in_the_workplace.md` | **Adds** a pets policy (POL-14). Before uploading, "Can I bring my dog to the office?" is refused | "Can I bring my dog to the office?" → yes, on Wednesdays and Fridays after registering; cited to POL-14 |
| `POL-02_paid_time_off_update.md` | **Replaces** the PTO policy; version goes from 1.0 to 1.1 automatically | "How many unused PTO days can I carry over?" → 8 (was 5), cited to POL-02 version 1.1 |

Before uploading, ask the question once to see the original answer (or refusal). After testing, use **Reset to original policies** on the admin page to restore the committed corpus.

Remove POL-14 after testing: the evaluation set expects the dog question to be refused (question Q24).

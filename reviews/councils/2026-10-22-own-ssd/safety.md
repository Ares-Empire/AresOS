Reviewed `46c68e4`. **One safety gap.** No files changed.

**1. Should-fix before physical release — the fitting and removal instructions omit a damaged-battery inspection and stop condition.**  
Location: [INSTALL.md §3](/C:/Users/pab/AresOS-10-own-ssd-install/docs/INSTALL.md:58), also reused by §9’s removal option.

- **Scenario:** After lifting the cover, the owner sees a visibly swollen or cracked battery, but the slot, screws and connector look normal. The instructions proceed directly to disconnecting the battery, fitting the SSD, reconnecting and powering on. The listed stop conditions cover clips, connectors and cover fit, but not the battery itself.
- **Impact:** Handling or reconnecting a damaged battery can worsen damage. Lenovo warns that excessive swelling can, in rare cases, create hazardous conditions and recommends professional replacement. [Lenovo battery guidance](https://pcsupport.lenovo.com/tt/en/products/laptops-and-netbooks/lenovo-b-series-laptops/b50-10/solutions/ht509084-battery-qa)
- **Fix:** Add a visual inspection before opening and immediately after removing the cover. A bulging, cracked, leaking or otherwise damaged battery means stop the fitting/removal procedure; do not press it flat, reconnect power or continue charging. Refer the owner to Lenovo or a qualified repairer. Apply this to undo as well.
- **Check:** In the novice walkthrough, present a photograph of an abnormally swollen battery with otherwise normal screws and connectors. The reader must stop before connector/SSD work or power reconnection.

Lenovo’s LOQ HMM explicitly requires checking for cracked or bulging batteries in its safety inspection, printed p. 3. I verified that text in the cached primary PDF; the live PDF download was unavailable during this review. :codex-file-citation{path="C:/Users/pab/AresOS-10-own-ssd-install/.work/lenovo_loq_hmm.pdf" purpose="source"}
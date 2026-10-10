# Final QA – integrácia galérie

Galéria má nové tlačidlo Finalizovať QA. Je zakázané bez explicitného `final_qa_evidence` z motora: FINAL_QA_APPROVED, overená identita, plastické šablóny, review_id a dva SHA-256.

Tlačidlo nevyvodzuje finálne schválenie z OK / Beriem. Po potvrdení používa `finalize_triplet` a zapisuje iba do lokálneho finálneho úložiska. Žiadne GitHub zápisy ani mazanie originálov.

Zostáva implementovať vydávanie dôkazov `final_qa_evidence` v renderovacom/QA motore; bez toho bude tlačidlo zámerne neaktívne.

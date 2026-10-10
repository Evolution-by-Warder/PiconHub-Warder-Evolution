# Oprava plánovača regenerácie

`_output_signature` teraz odmieta staré BLACK/WHITE varianty bez platných SHA-256 podpisov originálnych plastických šablón. Aj pri nezmenenom zdrojovom PNG sa preto zaradia na regeneráciu. Kontrola je fail-closed; nezverejňuje nič na GitHub.

Zostáva end-to-end test na Windows a automatický update.

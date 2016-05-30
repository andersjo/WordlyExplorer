curl localhost:8983/solr/humboldt/update?commit=true -d '<delete><query>*:*</query></delete>'
python scripts/import_reviews.py ~/Dropbox/Humboldt/united_kingdom.auto-adjusted_gender.NUTS-regions.CoNLL.jsonl --locations ~/Dropbox/Humboldt/mapped_locations.tsv --country-code uk
python scripts/import_reviews.py ~/Dropbox/Humboldt/denmark.auto-adjusted_gender.NUTS-regions.CoNLL.jsonl --locations ~/Dropbox/Humboldt/mapped_locations.tsv --country-code dk
python scripts/import_reviews.py ~/Dropbox/Humboldt/germany.auto-adjusted_gender.NUTS-regions.CoNLL.jsonl --locations ~/Dropbox/Humboldt/mapped_locations.tsv --country-code de
python scripts/import_reviews.py ~/Dropbox/Humboldt/france.auto-adjusted_gender.NUTS-regions.CoNLL.jsonl --locations ~/Dropbox/Humboldt/mapped_locations.tsv --country-code fr

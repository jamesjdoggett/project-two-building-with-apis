# Project #2: Building With APIs

### Question 1 – Defend your research decision.

I chose TVmaze because it was free, didn't require an API key, and had pretty much everything I needed for a TV show tracker. It lets users search for shows and provides information like descriptions, genres, and show IDs. I also considered Open Library, but I wasn't as interested in making a book tracker, and its system for organizing books seemed more complicated. Based on the official documentation and my research in `research/api-provider-comparison.md`, TVmaze seemed like the better choice for my project.

### Question 2 – Explain one prototype decision.

My prototype compared two ways of handling viewing status and episode progress. One option automatically updated the viewing status whenever progress changed, while the other kept them separate. I went with the second option because I didn't want the application changing someone's viewing status without them choosing to. This is handled in `shows/forms.py` and `shows/personal.py`, and users can edit both values through `shows/templates/shows/edit.html`.

### Question 3 – Trace your API update.

My second script, `scripts/test_showvault_api.py`, updates a show's rating through my own API. It sends a PATCH request to `/api/entries/<id>/`, which is routed through `config/urls.py` and `shows/api_urls.py`. The `EntryDetail` view in `shows/api.py` handles the request, and `PersonalSerializer` checks that the rating is valid before saving it to the `Entry` model in `shows/models.py`. Django identifies the user through session authentication, and the view checks that the entry belongs to that user before allowing changes. The script then makes another GET request to confirm the new rating was saved.

### Question 4 – Trace and verify your data.

The saved-show library is at `/library/`, and its view is in `shows/views.py` around line 188. The search and filtering code is in `shows/library.py`, where `title__icontains` searches show titles without worrying about capitalization. It also filters by the logged-in user and viewing status. These filters use normal Django querysets rather than Q objects, although Q objects are used in `shows/models.py` around line 46 to make sure ratings and episode progress are valid. Users can sort shows by title, rating, or date added, and the results are split into pages of 20 using `Paginator`. For example, searching for "Space" while filtering by Paused would only show saved titles containing that word with a Paused status. The same filtering logic is tested in `shows/test_library.py`, including sorting and pagination.

### Question 5 – Push back on the agent.

I didn't really make any changes after manually reviewing the finished application because everything seemed to work the way I expected. The agent did catch and fix a few issues during development, including one where saved episode progress wasn't displaying correctly and another where the library wasn't applying search filters properly. I also had the agent condense the original twelve-phase plan into six phases because I thought the original plan was unnecessarily long. Overall, I was satisfied with how the application turned out, so I didn't see a reason to request additional changes just for the sake of changing something.
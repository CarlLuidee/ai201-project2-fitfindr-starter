# FitFindr — planning.md

> Complete this document before writing any implementation code.
> Your spec and agent diagram are what you'll use to direct AI tools (Claude, Copilot, etc.) to generate your implementation — the more specific they are, the more useful the generated code will be.
> Your planning.md will be reviewed as part of your submission.
> Update it before starting any stretch features.

---

## Tools

List every tool your agent will use. For each tool, fill in all four fields.
You must have at least 3 tools. The three required tools are listed — add any additional tools below them.

### Tool 1: search_listings

**What it does:**
<!-- Describe what this tool does in 1–2 sentences -->
Searches the listings dataset and returns matching items.

**Input parameters:**
<!-- List each parameter, its type, and what it represents -->
- `description` (str): A description of the user's preferences, requirements, or desired features. This will be used to find the best-matching items from the `listings.json`.
- `size` (str): The dezired size of the item. Listings must match this size.
- `max_price` (float): The maximum acceptable price of the item. Only items priced at or below this amount will be considered.

**What it returns:**
<!-- Describe the return value — what fields does a result contain? -->
Returns a list of 3 matching item listings in their dict form sorted by relevance. 

**What happens if it fails or returns nothing:**
<!-- What should the agent do if no listings match? -->
Stop searching, inform the user that there are no matching listings, and suggest a different search topic.

---

### Tool 2: suggest_outfit

**What it does:**
<!-- Describe what this tool does in 1–2 sentences -->
Given a specific item and the user's current wardrobe, it suggests one or more complete outfit combinations.

**Input parameters:**
<!-- List each parameter, its type, and what it represents -->
- `new_item` (dict): The item that outfit combinations will be built around. The suggested outfits should incorporate this item and pair it with complementary items from the user's current wardrobe.
- `wardrobe` (dict): The user's current wardrobe. This will be used to create outfit combinations that complement the specified item.

**What it returns:**
<!-- Describe the return value -->
Returns the resulting outfit combination using the item specified by the user.

**What happens if it fails or returns nothing:**
<!-- What should the agent do if the wardrobe is empty or no outfit can be suggested? -->
Inform the user their wardrobe lacks items for outfit generation, and return an outfit using only the included item and general styling advice.

---

### Tool 3: create_fit_card

**What it does:**
<!-- Describe what this tool does in 1–2 sentences -->
Generates a short, shareable description of a complete outfit. The kind of thing someone would caption a social media post with. 

**Input parameters:**
<!-- List each parameter, its type, and what it represents -->
- `outfit` (str): Outfit suggested by `suggest_outfit`.
- `new_item` (dict): Listing selected from `search_listings`.

**What it returns:**
<!-- Describe the return value -->
Returns a description that complements the user's outfit.

**What happens if it fails or returns nothing:**
<!-- What should the agent do if the outfit data is incomplete? -->
Inform the user that the outfit data is incomplete.

---

### Additional Tools (if any)

<!-- Copy the block above for any tools beyond the required three -->

---

## Planning Loop

**How does your agent decide which tool to call next?**
<!-- Describe the logic your planning loop uses. What does it look at? What conditions change its behavior? How does it know when it's done? -->
The agent first calls `search_listings` to find matching thrift listings. If results are empty, set an error message in the session and return early. If it returns a list of items, it picks the best result, `result[0]`, calls `suggest_outfit`, and attempts to generate outfit recommendations using the best result and the user's wardrobe. If it returns no outfit, set an error message in the session and return early. If it returns an outfit, it calls `create_fit_card` with the outfit and the user's wardrobe, then attempts to create a shareable fit card. If it returns no fit card, set an error message in the session and return early. If it returns a fit card, display the result to the user.

---

## State Management

**How does information from one tool get passed to the next?**
<!-- Describe how your agent stores and accesses state within a session. What data is tracked? How is it passed between tool calls? -->
The agent passes outputs from one tool to the next through a shared session state. First, it calls `search_listings()` using the user's search criteria. If the returned results list is empty, the agent stores an error message in the session state and returns immediately. Otherwise, it selects the most relevant item, such as `results[0]`, and stores it as `selected_item`. Next, it calls `suggest_outfit(new_item=selected_item, wardrobe=wardrobe)`. If no outfits are returned, the agent stores an error message and returns early. If outfits are generated successfully, the top outfit is stored in the session state and passed to `create_fit_card(outfit, selected_item)`. If fit card generation fails, the agent records the error and returns. Otherwise, it stores the generated fit card and returns the completed recommendation.

---

## Error Handling

For each tool, describe the specific failure mode you're handling and what the agent does in response.

| Tool | Failure mode | Agent response |
|------|-------------|----------------|
| search_listings | No results match the query | Inform the user that no matching listings were found. Suggest changing their search criteria. Stop worflow. |
| suggest_outfit | Wardrobe is empty | Inform the user that a complete outfit cannot be generated because of limited wardrobe data, and generate basic styling advice. |
| create_fit_card | Outfit input is missing or incomplete | Inform the user that a fit card cannot be created without a complete outfit input. Stop worflow. |

---

## Architecture

<!-- Draw a diagram of your agent showing how the components connect:
     User input → Planning Loop → Tools (search_listings, suggest_outfit, create_fit_card)
                                                                          ↕
                                                                   State / Session
     Show what triggers each tool, how state flows between them, and where error paths branch off.
     ASCII art, a Mermaid diagram (https://mermaid.js.org/syntax/flowchart.html), or an embedded
     sketch are all fine. You'll share this diagram with an AI tool when asking it to implement
     the planning loop and each individual tool. -->                                    
User Query
    │
    ▼
Planning Loop
    │
    ▼
search_listings() -> empty results -> session["error"] -> return
    │
    ▼
session["best_item"]
    │
    ▼
suggest_outfit() -> no outfit -> session["error"] -> return
    │
    ▼
session["outfit_suggestion"]
    │
    ▼
create_fit_card() -> failure -> Session["error"] -> return
    │
    ▼
session["fit_card"]
    │
    ▼
return session

---

## AI Tool Plan

<!-- For each part of the implementation below, describe:
     - Which AI tool you plan to use (Claude, Copilot, ChatGPT, etc.)
     - What you'll give it as input (which sections of this planning.md, your agent diagram)
     - What you expect it to produce
     - How you'll verify the output matches your spec before moving on

     "I'll use AI to help me code" is not a plan.
     "I'll give Claude my Tool 1 spec (inputs, return value, failure mode) and ask it to implement
     search_listings() using load_listings() from the data loader — then test it against 3 queries
     before trusting it" is a plan. -->
I will use Claude to implement each tool individually by providing it with the corresponding sections in `planning.md`, including tool description, inputs, outputs, and failure modes, along with any relevant helper code, such as the data loader and agent diagram. For the LLM, Groq (llama-3.3-70b-versatile) will be used. I expect it to produce a clean implementation that adheres to the exact input/output contracts and handles errors as specified. After each tool is generated, I will verify it by running at least 3 test cases to ensure it behaves correctly before moving on to the next tool.

**Milestone 3 — Individual tool implementations:**

**Milestone 4 — Planning loop and state management:**

---

## A Complete Interaction (Step by Step)

Write out what a full user interaction looks like from start to finish — tool call by tool call. Use a specific example query.

**Example user query:** "I'm looking for a vintage graphic tee under $30. I mostly wear baggy jeans and chunky sneakers. What's out there and how would I style it?"

**Step 1:**
<!-- What does the agent do first? Which tool is called? With what input? -->
The user describes what outfit they want, and the agent calls `search_listings` using the user's search criteria.

**Step 2:**
<!-- What happens next? What was returned from step 1? What tool is called now? -->
If matching listing items from `search_listings` are returned, the agent picks the best result, calls `suggest_outfit` with the best result and the user's wardrobe, and then suggests a new outfit to the user.

**Step 3:**
<!-- Continue until the full interaction is complete -->
If an outfit is returned from `suggest_outfit`, the agent calls `create_fit_card` using the outfit from `suggest_outfit` and the item from the best result from `search_listings` to generate a short description of the outfit.

**Final output to user:**
<!-- What does the user actually see at the end? -->
"Faded Band Tee — $22, Depop, Good condition."
"Pair this with your wide-leg jeans and platform Docs for a classic 90s grunge look. Roll the sleeves once and tuck the front corner slightly for shape."
"Thrifted this faded band tee off depop for $22 and honestly it was made for my wide-legs 🖤 full look in my stories"
# Similarity Detection Improvements

- [x] 1. Normalize titles using word sorting (remove stopwords, sort tokens)
- [x] 2. Use fuzzy ingredient name matching (Levenshtein distance ~0.85)
- [x] 3. Weight ingredients by category importance (proteins 5x, veggies 3x, spices 0.5x)
- [x] 4. Detect cooking method overlap (extract keywords, penalize matching methods)
- [x] 5. Penalize similar recipe complexity (ingredient_count + step_count)

# Vegetable-Focused Improvements

- [x] 1. Calculate vegetable ratio per recipe (count veggies, calculate percentage)
  → Added is_vegetable() and calculate_vegetable_ratio() functions
- [x] 4. Penalty for vegetable-poor recipe pairs (reduce score when both low-veggie)
  → Added -6 penalty in similarity_score when both recipes <25% vegetables
- [x] 5. Track weekly vegetable variety target (monitor diversity, reject if below threshold)
  → Added count_unique_vegetables() and warning when menu has <15 unique vegetables

**Skipped:** #2 (minimum vegetable threshold filter), #3 (boost similarity for vegetable diversity)

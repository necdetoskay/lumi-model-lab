from experiments.prototypes import story_spine_refined_recipe_20260926 as base


if __name__ == "__main__":
    base.WRITER_MODEL = "mistralai/mistral-small-2603"
    base.main()

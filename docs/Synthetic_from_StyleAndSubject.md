# Tentative Workflow
- Create work directory `outputs/style_subject` store every intermediate input and output file within this directory

1. sample from test dataset `data/test-0000*arabic.csv`
- input: `--input-file data/test-00000-of-00001.arabic.csv`
- only select grade >= 9: apply flag `--filter-grade "9,10,11,12"` and `--mode stratified --stratify-col grade`
- sample from each subjects and n_sample from the following chart
    | subject | n_seeds|
    |Social   |      10|
    |Physics  |       6|
    |Biology  |       6|
    |Science  |       4|
    |Islamic Studies |  3|
    apply flags: `--filter-subject {subject}` and `--n {n_seeds}`
- output seed files for each subject
example command: 
```
    arabic-synth sample-and-convert exams --input-file data/test-00000-of-00001.arabic.csv --output-file outputs/test_style_prompt/physics_seeds.jsonl --n 7 --filter-grade "9,10,11,12" --filter-subject "Physics" --mode stratified --stratify-col grade --seed 101
```
- output seed file names: `{output_dir}/{subject}_seed.jsonl`

2. use seed file and style guide prompt to generate synthetic data
- use seeds `--seed-file {output_dir}/{subject}_seed.jsonl` and corresponding subject inforcement for prompt `--subject {subject}`
- generate n_seeds*600 samples `--num_samples {n_seeds*600}` 
example command:
```
 arabic-synth generate exams --output-dir outputs/test_style_prompt/ --seed-file outputs/test_style_prompt/physics_seeds.jsonl --model openai:gpt-4o --num-samples 200 --subject physics
 ```

3. clean and evaluate output
example command:
```
arabic-synth clean exams --in-path outputs/style_guide_test/generate_style_200.jsonl --out-path outputs/exams_clean.jsonl
arabic-synth evaluate-style exams --in-path outputs/exams_clean.jsonl
```
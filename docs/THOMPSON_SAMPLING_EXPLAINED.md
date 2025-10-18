# 🎲 Thompson Sampling - How It Works

## 📚 What is Thompson Sampling?

Thompson Sampling is a **Bayesian multi-armed bandit algorithm** that automatically balances:
- **Exploration** - Trying new experiments to gather data
- **Exploitation** - Using proven winners more often

Think of it like this: You have 3 slot machines (experiments). Which one should you pull next?
- A greedy algorithm always pulls the current best → might miss a better option
- Random selection wastes time on bad options
- **Thompson Sampling** intelligently balances trying all of them while favoring winners

---

## 🧮 The Math (Simplified)

### Beta Distribution

Each experiment tracks two parameters:
- **α (alpha)** = successes + 1 (starts at 1)
- **β (beta)** = failures + 1 (starts at 1)

**Starting values:** α=1, β=1 (uniform prior - no preference)

### How Selection Works

For each lead, the system:

1. **Samples** a random number from Beta(α, β) for each experiment
   ```python
   sample = random.betavariate(exp.alpha, exp.beta)
   ```

2. **Picks the experiment** with the highest sample
   ```python
   best_experiment = experiment_with_max(samples)
   ```

3. **Updates parameters** based on conversion:
   - If lead converts → α = α + 1 (success!)
   - If lead doesn't convert → β = β + 1 (failure)

---

## 🎯 Real Example from Your System

### Initial State (No Data)

```
Experiment A: α=1, β=1 (uniform - no preference)
Experiment B: α=1, β=1 (uniform - no preference)
Experiment C: α=1, β=1 (uniform - no preference)
```

**Selection:** All equally likely (~33% each)

### After 10 Leads (Some Conversions)

```
Experiment A: α=4, β=1 (3 successes, 0 failures)
  Success rate: 3/3 = 100% ✓

Experiment B: α=5, β=1 (4 successes, 0 failures)
  Success rate: 4/4 = 100% ✓✓

Experiment C: α=3, β=1 (2 successes, 0 failures)
  Success rate: 2/2 = 100% ✓
```

**Selection:** Experiment B selected more often (has more data + high success)

### After 100 Leads (Clear Winner Emerges)

```
Experiment A: α=25, β=11 (24 successes, 10 failures)
  Success rate: 24/34 = 70.6% 🟡

Experiment B: α=45, β=6 (44 successes, 5 failures)
  Success rate: 44/49 = 89.8% 🟢 WINNER!

Experiment C: α=15, β=21 (14 successes, 20 failures)
  Success rate: 14/34 = 41.2% 🔴
```

**Selection Distribution:**
- Experiment B: ~70% (clear winner)
- Experiment A: ~25% (still exploring)
- Experiment C: ~5% (rarely selected)

---

## 🔍 How Your System Uses It

### Code Location
`services/workers/outreach_orchestrator_worker.py:58-96`

```python
def select_experiment(db: Session, lead: Lead) -> Optional[Experiment]:
    """Select experiment using Thompson Sampling"""
    import random

    # Get all active experiments
    experiments = db.query(Experiment).filter(Experiment.is_active == True).all()

    # Thompson Sampling: sample from Beta distribution
    best_experiment = None
    best_sample = -1

    for exp in experiments:
        # Sample from Beta(alpha, beta)
        sample = random.betavariate(exp.alpha, exp.beta)

        if sample > best_sample:
            best_sample = sample
            best_experiment = exp

    return best_experiment
```

### When It Runs

**Flow:**
1. Lead is scored by OpenAI → Published to `leads.scored` Kafka topic
2. **Outreach Orchestrator Worker** consumes the event
3. **Thompson Sampling** selects the best experiment
4. Message is personalized using the selected template
5. Outreach is sent via Lightfield
6. Conversion data updates α/β parameters (feedback loop)

---

## 📊 Visualization

### Beta Distribution Curves

**Early Stage (α=1, β=1):**
```
Wide, flat distribution - high uncertainty
     *****
    *     *
   *       *
  *         *
 *           *
*_____________*
0.0         1.0
```
**Interpretation:** Could be anywhere from 0% to 100% success rate

**After Success (α=5, β=1):**
```
Narrow, right-skewed - confident it's good
              ******
             *      *
            *        *
           *          *
          *            *
*________*              *
0.0                   1.0
```
**Interpretation:** Likely 80-90% success rate

**After Failures (α=1, β=5):**
```
Narrow, left-skewed - confident it's bad
*******
*      *
*       *
*        *
*         *
*          *__________*
0.0                   1.0
```
**Interpretation:** Likely 10-20% success rate

---

## 🎮 Interactive Demo

Run this to see Thompson Sampling in action:

```bash
PYTHONPATH=apps/agent-api apps/agent-api/.venv/bin/python -c "
import random
from app.models.base import SessionLocal
from app.models.experiment import Experiment

db = SessionLocal()
experiments = db.query(Experiment).filter(Experiment.is_active == True).all()

print('🎲 Thompson Sampling - 10 Rounds')
print()

for round_num in range(1, 11):
    print(f'Round {round_num}:')

    for exp in experiments:
        sample = random.betavariate(exp.alpha, exp.beta)
        print(f'  {exp.name[:25]:25s}: {sample:.4f}')

    print()

db.close()
"
```

---

## 🧠 Why It's Smart

### Problem: Exploration vs Exploitation Dilemma

**Greedy Algorithm:**
```
Round 1: Try A, B, C → B is best so far
Round 2-100: Only use B
```
❌ **Issue:** What if A or C would have been better with more data?

**Random Selection:**
```
Round 1-100: Randomly pick A, B, or C
```
❌ **Issue:** Wastes 67% of leads on suboptimal experiments

**Thompson Sampling:**
```
Round 1-10: Try all fairly equally (exploration)
Round 11-50: Favor winners but still explore losers
Round 51-100: Mostly use winner, rarely try others
```
✅ **Winner:** Automatically balances both!

### Mathematical Guarantees

Thompson Sampling has **proven convergence properties**:
- **Regret bound:** O(log T) - near-optimal performance
- **Bayesian optimal:** Maximizes expected reward under uncertainty
- **No hyperparameters:** α/β update automatically from data

---

## 🎯 Real-World Impact

### Your Demo Data

**Current State:**
```
Enterprise Formal:   α=4, β=1 → 100% success (3 trials)
Enterprise Casual:   α=5, β=1 → 100% success (4 trials)
SMB Value:          α=3, β=1 → 100% success (2 trials)
```

**Selection Distribution:**
- All three are performing well
- Casual Tone gets selected slightly more (has more data)
- System still explores all three to gather more information

**After 1000 Leads:**
```
Enterprise Formal:   α=250, β=150 → 62.5% conversion
Enterprise Casual:   α=400, β=100 → 80.0% conversion ← WINNER
SMB Value:          α=180, β=220 → 45.0% conversion
```

**Selection Distribution:**
- Casual Tone: ~70% of leads (proven winner)
- Formal Tone: ~25% of leads (decent performer)
- SMB Value: ~5% of leads (low performer)

**Result:** System automatically learned which message works best!

---

## 🔄 Feedback Loop

### How Parameters Update

**Code Location:**
`services/workers/feedback_worker.py` (Phase 3)

```python
def update_experiment_from_conversion(db: Session, experiment_id: str):
    """Update experiment parameters when lead converts"""
    experiment = db.query(Experiment).filter_by(experiment_id=experiment_id).first()

    if experiment:
        # Increment alpha (success count)
        experiment.alpha += 1
        db.commit()
```

**Conversion Event:**
```json
{
  "event_type": "conversion",
  "lead_id": "lead_123",
  "experiment_id": "exp_casual_v1",
  "timestamp": "2025-10-17T10:30:00Z"
}
```

**Automatic Update:**
```
BEFORE: α=5, β=1
AFTER:  α=6, β=1  (one more success!)
```

---

## 🎤 Explaining to Judges

### Simple Explanation

> **"Thompson Sampling is like a smart slot machine player."**
>
> **"Instead of always pulling the best machine or trying them randomly, it uses Bayesian statistics to balance exploring new options while exploiting proven winners."**
>
> **"The α and β parameters you see in the dashboard are success/failure counts. As leads convert, these update automatically, and the system learns which messages work best."**

### Technical Explanation

> **"We use a Beta distribution as a Bayesian prior for each experiment's conversion rate."**
>
> **"For each lead, we sample from Beta(α, β) for each experiment and select the one with the highest sample. This naturally balances exploration and exploitation."**
>
> **"As conversion data comes in, we update the posteriors using Bayesian inference - α increases for successes, β for failures."**
>
> **"This gives us regret bounds of O(log T), which is near-optimal for the multi-armed bandit problem."**

---

## 📖 Further Reading

**Papers:**
- [Thompson Sampling for Contextual Bandits](https://arxiv.org/abs/1209.3352)
- [Analysis of Thompson Sampling](https://arxiv.org/abs/1111.1797)

**Tutorials:**
- [A Tutorial on Thompson Sampling](https://web.stanford.edu/~bvr/pubs/TS_Tutorial.pdf)
- [Bayesian Bandits](https://towardsdatascience.com/bayesian-bandits-6c8e21e80b65)

**Your Implementation:**
- Code: `services/workers/outreach_orchestrator_worker.py:58-96`
- Database: `apps/agent-api/app/models/experiment.py`
- Feedback: `services/workers/feedback_worker.py`

---

## ✅ Key Takeaways

1. **Thompson Sampling is Bayesian** - Uses Beta distributions to model uncertainty
2. **Automatically balances exploration/exploitation** - No manual tuning needed
3. **Updates from feedback** - Learns which experiments work best over time
4. **Mathematically optimal** - Proven regret bounds of O(log T)
5. **Production-ready** - Simple to implement, no hyperparameters to tune

---

**This is why your system is autonomous - it learns by itself!** 🤖🎯

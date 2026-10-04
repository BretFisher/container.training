# Executing batch jobs

- Deployments are great for stateless web apps

  (as well as workers that keep running forever)

- Pods are great for one-off execution that we don't care about

  (because they don't get automatically restarted if something goes wrong)

- Jobs are great for work that must run *until it completes*

  (e.g. a database migration, a backup, a batch of data to process)

- CronJobs are great to run Jobs at regular intervals

  (just like the classic UNIX `cron` daemon with its `crontab` files)

---

## Jobs

- A Job creates a Pod, and makes sure that it *completes successfully*

- If the Pod fails (or its node fails), the Job creates another Pod

- The Job keeps trying until:

  - either a Pod succeeds,

  - or we hit the *backoff limit* of the Job (default=6)

- When the Job is done, its Pods stay, so we can read their logs

- Example:

  ```bash
  kubectl create job flipcoin --image=alpine -- sh -c 'exit $(($RANDOM%2))'
  ```

---

## CronJobs

- A CronJob creates a Job at specific intervals

  (CronJob → Job → Pod)

- Its *schedule* uses the standard cron format

  (e.g. `*/3 * * * *` means "every three minutes")

- Make sure that the Job terminates!

  (by default, a CronJob doesn't wait for the previous Job to finish)

- Example:

  ```bash
  kubectl create cronjob every3mins --schedule="*/3 * * * *" \
          --image=alpine -- sleep 10
  ```

???

:EN:- Running batch and cron jobs (short version)
:FR:- Tâches périodiques *(cron)* et traitement par lots *(batch)* (version courte)

// Pattern: Chain of Responsibility. Each Rule inspects the context, may record
// problems, and hands the context to the next Rule. New checks are added by
// linking another Rule; existing ones never change.
export class Rule {
  constructor(check) {
    this.check = check;
    this.next = null;
  }

  then(next) {
    this.next = next;
    return next;
  }

  run(context, errors = {}, stopOnFirst = false) {
    this.check(context, errors);
    if (stopOnFirst && Object.keys(errors).length) return errors;
    return this.next ? this.next.run(context, errors, stopOnFirst) : errors;
  }
}

export const chain = (...rules) => {
  rules.reduce((previous, rule) => previous.then(rule));
  return rules[0];
};

export const createContractMutationGate = () => {
  let locked = false;
  return {
    tryEnter() {
      if (locked) return false;
      locked = true;
      return true;
    },
    leave() {
      locked = false;
    },
    isLocked() {
      return locked;
    },
  };
};

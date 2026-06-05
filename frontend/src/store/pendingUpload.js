import { reactive } from 'vue'

const state = reactive({
  files: [],
  simulationRequirement: '',
  limits: {},
  isPending: false
})

export function setPendingUpload(files, requirement, limits = {}) {
  state.files = files
  state.simulationRequirement = requirement
  state.limits = limits
  state.isPending = true
}

export function getPendingUpload() {
  return {
    files: state.files,
    simulationRequirement: state.simulationRequirement,
    limits: state.limits,
    isPending: state.isPending
  }
}

export function clearPendingUpload() {
  state.files = []
  state.simulationRequirement = ''
  state.limits = {}
  state.isPending = false
}

export default state

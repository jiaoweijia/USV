"""
Multi-USV Model Identification Script
========================================
Based on the paper methodology:
1. Three homogeneous twin-propeller USVs execute identical maneuver sequences
2. Per-boat Savitzky-Golay smoothing and finite-difference acceleration computation
3. Per-boat data normalization (StandardScaler) to eliminate dimensional differences
4. Pooled dataset construction for joint identification
5. SLSQP optimization with physics-based box constraints
6. Leave-one-boat-out cross-validation for generalization assessment

Model structure (21 parameters, 7 per DOF):
  du = a1*v*r + a2*u + a3*v + a4*r + a5*Tp + a6*Ts + a7
  dv = b1*u*r + b2*u + b3*v + b4*r + b5*Tp + b6*Ts + b7
  dr = c1*u*v + c2*u + c3*v + c4*r + c5*Tp + c6*Ts + c7
"""
#多船模型辨识 ：从实验数据用 SLSQP 辨识 21 参数动力学模型（论文方法）
import numpy as np
from scipy.optimize import minimize
from scipy.signal import savgol_filter
import matplotlib.pyplot as plt
import pandas as pd
from sklearn.preprocessing import StandardScaler
import seaborn as sns
from matplotlib.colors import LinearSegmentedColormap
from matplotlib.ticker import MaxNLocator


# ========================================
# 1. Configuration
# ========================================
dt = 0.1
SAVGOL_WINDOW = 5
SAVGOL_POLYORDER = 2
N_PARAMS = 21
START_ROW = 0
N_ROWS = 450

boat_files = [
    'data/usv1_data.xlsx',
    'data/usv2_data.xlsx',
    'data/usv3_data.xlsx'
]
boat_names = ['USV1', 'USV2', 'USV3']
n_boats = len(boat_files)

# Physics-based box constraints for SLSQP
# Order: a1..a7, b1..b7, c1..c7
param_bounds = [
    (-10, 10),   # a1: v*r cross-coupling
    (-10, 0),    # a2: surge linear damping (negative)
    (-10, 10),   # a3: v coupling in surge
    (-10, 10),   # a4: r coupling in surge
    (0, 10),     # a5: Tp thrust in surge (positive)
    (0, 10),     # a6: Ts thrust in surge (positive)
    (-10, 10),   # a7: bias
    (-10, 10),   # b1: u*r cross-coupling
    (-10, 10),   # b2: u coupling in sway
    (-10, 0),    # b3: sway linear damping (negative)
    (-10, 10),   # b4: r coupling in sway
    (-10, 0),   # b5: Tp thrust in sway
    (0, 10),   # b6: Ts thrust in sway
    (-10, 10),   # b7: bias
    (-10, 10),   # c1: u*v cross-coupling
    (-10, 10),   # c2: u coupling in yaw
    (-10, 10),   # c3: v coupling in yaw
    (-10, 0),    # c4: yaw linear damping (negative)
    (-10, 0),     # c5: Tp thrust in yaw (positive)
    (0, 10),     # c6: Ts thrust in yaw (positive)
    (-10, 10),   # c7: bias
]


# ========================================
# 2. Angle processing utilities
# ========================================
def unwrap_angle(psi_deg):
    psi_rad = psi_deg * np.pi / 180.0
    return np.unwrap(psi_rad)


# ========================================
# 3. Per-boat data preprocessing
# ========================================
def preprocess_boat_data(df, dt=0.1):
    x = df['x'].values
    y = df['y'].values
    psi_deg = df['Heading'].values
    Ts = df['PWM_R'].values
    Tp = df['PWM_L'].values
    u = df['u'].values
    v = df['v'].values

    # Compute yaw rate from heading
    psi_rad = unwrap_angle(psi_deg)
    r = np.gradient(psi_rad, dt)

    # Smooth state variables
    u_s = savgol_filter(u, SAVGOL_WINDOW, SAVGOL_POLYORDER)
    v_s = savgol_filter(v, SAVGOL_WINDOW, SAVGOL_POLYORDER)
    r_s = savgol_filter(r, SAVGOL_WINDOW, SAVGOL_POLYORDER)

    # Compute accelerations via finite difference
    du = np.gradient(u_s, dt)
    dv = np.gradient(v_s, dt)
    dr = np.gradient(r_s, dt)

    return {
        'x': x, 'y': y, 'psi': psi_rad,
        'u': u_s, 'v': v_s, 'r': r_s,
        'du': du, 'dv': dv, 'dr': dr,
        'Tp': Tp, 'Ts': Ts, 'N': len(x)
    }


# ========================================
# 4. Normalization per boat
# ========================================
def normalize_boat(data):
    state_cols = ['u', 'v', 'r']
    deriv_cols = ['du', 'dv', 'dr']
    ctrl_cols = ['Tp', 'Ts']

    all_cols = state_cols + deriv_cols + ctrl_cols
    scaler = StandardScaler()
    stacked = np.column_stack([data[c] for c in all_cols])
    stacked_norm = scaler.fit_transform(stacked)

    norm_data = {}
    for i, c in enumerate(all_cols):
        norm_data[c] = stacked_norm[:, i]
    norm_data['x'] = data['x']
    norm_data['y'] = data['y']
    norm_data['psi'] = data['psi']
    norm_data['N'] = data['N']
    norm_data['scaler'] = scaler

    return norm_data


# ========================================
# 5. Build regression matrices (per boat)
# ========================================
def build_regression_data(data, normed=True):
    if normed:
        u, v, r = data['u'], data['v'], data['r']
        du, dv, dr = data['du'], data['dv'], data['dr']
        Tp, Ts = data['Tp'], data['Ts']
    else:
        u, v, r = data['u'], data['v'], data['r']
        du, dv, dr = data['du'], data['dv'], data['dr']
        Tp, Ts = data['Tp'], data['Ts']

    # Use all samples except last (due to finite difference alignment)
    n = data['N'] - 1
    u, v, r = u[:-1], v[:-1], r[:-1]
    Tp, Ts = Tp[:-1], Ts[:-1]
    du, dv, dr = du[1:], dv[1:], dr[1:]

    # Feature matrix for each channel (N x 7)
    X_du = np.column_stack([v * r, u, v, r, Tp, Ts, np.ones(n)])
    X_dv = np.column_stack([u * r, u, v, r, Tp, Ts, np.ones(n)])
    X_dr = np.column_stack([u * v, u, v, r, Tp, Ts, np.ones(n)])

    # Block-diagonal feature matrix (3N x 21)
    X_block = np.zeros((3 * n, N_PARAMS))
    X_block[0 * n:1 * n, 0:7] = X_du
    X_block[1 * n:2 * n, 7:14] = X_dv
    X_block[2 * n:3 * n, 14:21] = X_dr

    # Target vector (3N,)
    y_stack = np.concatenate([du, dv, dr])

    return X_block, y_stack, n


# ========================================
# 6. Model prediction (nonlinear form)
# ========================================
def model_equations(params, X, U):
    a = params[0:7]
    b = params[7:14]
    c = params[14:21]

    u_vec, v_vec, r_vec = X[:, 0], X[:, 1], X[:, 2]
    Ts_vec, Tp_vec = U[:, 0], U[:, 1]

    du = a[0] * v_vec * r_vec + a[1] * u_vec + a[2] * v_vec + a[3] * r_vec + a[4] * Tp_vec + a[5] * Ts_vec + a[6]
    dv = b[0] * u_vec * r_vec + b[1] * u_vec + b[2] * v_vec + b[3] * r_vec + b[4] * Tp_vec + b[5] * Ts_vec + b[6]
    dr = c[0] * u_vec * v_vec + c[1] * u_vec + c[2] * v_vec + c[3] * r_vec + c[4] * Tp_vec + c[5] * Ts_vec + c[6]

    return np.column_stack((du, dv, dr))


def loss_function(params, X, U, dX):
    pred = model_equations(params, X, U)
    error = pred - dX
    return np.sum(error ** 2)


# ========================================
# 7. Simulation with kinematics (for validation)
#    Parameters are estimated in normalized space, so we normalize
#    inputs, predict derivatives, then un-normalize at each step.
# ========================================
def predict_normalized(params, u, v, r, Tp, Ts, scaler):
    mu = scaler.mean_
    sigma = scaler.scale_
    u_n = (u - mu[0]) / sigma[0]
    v_n = (v - mu[1]) / sigma[1]
    r_n = (r - mu[2]) / sigma[2]
    Tp_n = (Tp - mu[6]) / sigma[6]
    Ts_n = (Ts - mu[7]) / sigma[7]

    a = params[0:7]
    b = params[7:14]
    c = params[14:21]

    du_n = a[0] * v_n * r_n + a[1] * u_n + a[2] * v_n + a[3] * r_n + a[4] * Tp_n + a[5] * Ts_n + a[6]
    dv_n = b[0] * u_n * r_n + b[1] * u_n + b[2] * v_n + b[3] * r_n + b[4] * Tp_n + b[5] * Ts_n + b[6]
    dr_n = c[0] * u_n * v_n + c[1] * u_n + c[2] * v_n + c[3] * r_n + c[4] * Tp_n + c[5] * Ts_n + c[6]

    du = du_n * sigma[3] + mu[3]
    dv = dv_n * sigma[4] + mu[4]
    dr = dr_n * sigma[5] + mu[5]

    return du, dv, dr


def simulate_with_params(params, raw_data, scaler, x0, y0, psi0, dt, N):
    u_sim = np.zeros(N)
    v_sim = np.zeros(N)
    r_sim = np.zeros(N)
    x_sim = np.zeros(N)
    y_sim = np.zeros(N)
    psi_sim = np.zeros(N)

    u_sim[0], v_sim[0], r_sim[0] = raw_data['u'][0], raw_data['v'][0], raw_data['r'][0]
    x_sim[0], y_sim[0], psi_sim[0] = x0, y0, psi0

    for k in range(1, N):
        Ts = raw_data['Ts'][k-1]
        Tp = raw_data['Tp'][k-1]

        u_cur = u_sim[k-1]
        v_cur = v_sim[k-1]
        r_cur = r_sim[k-1]
        psi_cur = psi_sim[k-1]

        du, dv, dr = predict_normalized(params, u_cur, v_cur, r_cur, Tp, Ts, scaler)

        u_sim[k] = u_cur + dt * du
        v_sim[k] = v_cur + dt * dv
        r_sim[k] = r_cur + dt * dr

        x_sim[k] = x_sim[k-1] + dt * (u_cur * np.cos(psi_cur) - v_cur * np.sin(psi_cur))
        y_sim[k] = y_sim[k-1] + dt * (u_cur * np.sin(psi_cur) + v_cur * np.cos(psi_cur))
        psi_sim[k] = psi_cur + dt * r_cur
        psi_sim[k] = (psi_sim[k] + np.pi) % (2 * np.pi) - np.pi

    return x_sim, y_sim, psi_sim, u_sim, v_sim, r_sim


# ========================================
# 8. Load and preprocess all boats
# ========================================
print("=" * 60)
print("Multi-USV Model Identification")
print("=" * 60)

raw_data = []
for i, f in enumerate(boat_files):
    df = pd.read_excel(f).iloc[START_ROW:START_ROW+N_ROWS]
    data = preprocess_boat_data(df, dt)
    raw_data.append(data)
    print(f"{boat_names[i]}: {data['N']} samples (rows {START_ROW}~{START_ROW+N_ROWS-1}), "
          f"u range [{data['u'].min():.3f}, {data['u'].max():.3f}], "
          f"r range [{data['r'].min():.3f}, {data['r'].max():.3f}]")

# ========================================
# 9. Per-boat normalization
# ========================================
print("\n--- Step 1: Per-boat Normalization ---")
norm_data = []
for i in range(n_boats):
    nd = raw_data[i]
    nd = normalize_boat(raw_data[i])
    norm_data.append(nd)
    scaler = nd['scaler']
    means = scaler.mean_
    stds = scaler.scale_
    print(f"{boat_names[i]} normalization stats:")
    print(f"  Means:  u={means[0]:.4f}, v={means[1]:.4f}, r={means[2]:.4f}, "
          f"du={means[3]:.4f}, dv={means[4]:.4f}, dr={means[5]:.4f}, "
          f"Tp={means[6]:.4f}, Ts={means[7]:.4f}")
    print(f"  Stds:   u={stds[0]:.4f}, v={stds[1]:.4f}, r={stds[2]:.4f}, "
          f"du={stds[3]:.4f}, dv={stds[4]:.4f}, dr={stds[5]:.4f}, "
          f"Tp={stds[6]:.4f}, Ts={stds[7]:.4f}")

# ========================================
# 10. Build pooled regression dataset
# ========================================
print("\n--- Step 2: Pooled Dataset Construction ---")
X_list = []
y_list = []
n_list = []

for i in range(n_boats):
    X_i, y_i, n_i = build_regression_data(norm_data[i], normed=True)
    X_list.append(X_i)
    y_list.append(y_i)
    n_list.append(n_i)
    print(f"{boat_names[i]}: {n_i} samples per channel → {3 * n_i} regression samples")

X_pool = np.vstack(X_list)
y_pool = np.concatenate(y_list)
K_pool = len(y_pool)
print(f"Pooled dataset: {K_pool} total regression samples "
      f"({K_pool // 3} per channel)")

# ========================================
# 11. Initial parameter guess
# ========================================
initial_params = np.array([
    -1.1391,   0.0028,  0.6836,  0.6836,  0.6836,  0.6836,  0.6836,   # a1-a7
     0.0161,  -0.0052,  0.0020,  0.0068,  0.0020,  0.0068,  0.0161,   # b1-b7
     8.2861,  -0.9860,  0.0307,  1.3276,  0.0307,  1.3276,  0.0010    # c1-c7
])

# ========================================
# 12. SLSQP optimization on pooled data (with constraints)
# ========================================
print("\n--- Step 3: SLSQP Optimization with Physical Constraints ---")
opt_bounds = param_bounds

def loss_regression(params, X_block, y):
    pred = X_block @ params
    return np.sum((pred - y) ** 2)

result_pool = minimize(
    loss_regression, initial_params,
    args=(X_pool, y_pool),
    method='SLSQP', bounds=opt_bounds,
    options={'disp': True, 'maxiter': 2000}
)

if result_pool.success:
    theta_pool = result_pool.x
    print("Pooled optimization converged!")
    print(f"Final loss: {result_pool.fun:.6f}")
else:
    print("Pooled optimization failed: " + result_pool.message)
    theta_pool = result_pool.x

# ========================================
# 13. Print identified model
# ========================================
a_est = theta_pool[0:7]
b_est = theta_pool[7:14]
c_est = theta_pool[14:21]

print("\n--- Identified Unified Model ---")
print(f"du = {a_est[0]:.6f}*v*r + {a_est[1]:.6f}*u + {a_est[2]:.6f}*v + {a_est[3]:.6f}*r + {a_est[4]:.6f}*Tp + {a_est[5]:.6f}*Ts + {a_est[6]:.6f}")
print(f"dv = {b_est[0]:.6f}*u*r + {b_est[1]:.6f}*u + {b_est[2]:.6f}*v + {b_est[3]:.6f}*r + {b_est[4]:.6f}*Tp + {b_est[5]:.6f}*Ts + {b_est[6]:.6f}")
print(f"dr = {c_est[0]:.6f}*u*v + {c_est[1]:.6f}*u + {c_est[2]:.6f}*v + {c_est[3]:.6f}*r + {c_est[4]:.6f}*Tp + {c_est[5]:.6f}*Ts + {c_est[6]:.6f}")

# ========================================
# 14. Leave-one-boat-out Cross-Validation
# ========================================
print("\n--- Step 4: Leave-One-Boat-Out Cross-Validation ---")

cv_results = {}
for test_idx in range(n_boats):
    train_indices = [j for j in range(n_boats) if j != test_idx]

    X_train = np.vstack([X_list[j] for j in train_indices])
    y_train = np.concatenate([y_list[j] for j in train_indices])
    X_test = X_list[test_idx]
    y_test = y_list[test_idx]

    result_cv = minimize(
        loss_regression, initial_params,
        args=(X_train, y_train),
        method='SLSQP', bounds=opt_bounds,
        options={'disp': False, 'maxiter': 2000}
    )

    theta_cv = result_cv.x

    # Prediction on training boats (self-prediction)
    y_train_pred = X_train @ theta_cv
    n_train_total = len(y_train)
    mse_train_du = np.mean((y_train_pred[0:n_train_total//3] - y_train[0:n_train_total//3]) ** 2) * (n_train_total // 3 > 0)
    # Actually, let's compute per-boat per-channel errors
    train_errors = {}
    for j in train_indices:
        Xj = X_list[j]
        yj = y_list[j]
        yj_pred = Xj @ theta_cv
        nj = n_list[j]
        mse_du = np.mean((yj_pred[0:nj] - yj[0:nj]) ** 2)
        mse_dv = np.mean((yj_pred[nj:2*nj] - yj[2*nj:3*nj]) ** 2)
        mse_dr = np.mean((yj_pred[2*nj:3*nj] - yj[2*nj:3*nj]) ** 2)
        train_errors[boat_names[j]] = {'du': mse_du, 'dv': mse_dv, 'dr': mse_dr, 'total': mse_du + mse_dv + mse_dr}

    # Prediction on test boat (cross-prediction)
    X_test = X_list[test_idx]
    y_test = y_list[test_idx]
    y_test_pred = X_test @ theta_cv
    n_test = n_list[test_idx]
    mse_du_test = np.mean((y_test_pred[0:n_test] - y_test[0:n_test]) ** 2)
    mse_dv_test = np.mean((y_test_pred[n_test:2*n_test] - y_test[2*n_test:3*n_test]) ** 2)
    mse_dr_test = np.mean((y_test_pred[2*n_test:3*n_test] - y_test[2*n_test:3*n_test]) ** 2)

    test_boat = boat_names[test_idx]
    train_boats_str = "+".join([boat_names[j] for j in train_indices])

    print(f"\n  Train: {train_boats_str} → Test: {test_boat}")
    print(f"  Training set MSE:")
    for bname, errs in train_errors.items():
        print(f"    {bname}: du={errs['du']:.6f}, dv={errs['dv']:.6f}, dr={errs['dr']:.6f}")
    print(f"  Cross-validation MSE on {test_boat}:")
    print(f"    du={mse_du_test:.6f}, dv={mse_dv_test:.6f}, dr={mse_dr_test:.6f}")

    cv_results[test_idx] = {
        'train_errors': train_errors,
        'test_errors': {'du': mse_du_test, 'dv': mse_dv_test, 'dr': mse_dr_test}
    }

# Self-prediction with pooled model
print("\n--- Self-Prediction using Pooled Model ---")
for i in range(n_boats):
    X_i = X_list[i]
    y_i = y_list[i]
    y_i_pred = X_i @ theta_pool
    n_i = n_list[i]
    mse_du_i = np.mean((y_i_pred[0:n_i] - y_i[0:n_i]) ** 2)
    mse_dv_i = np.mean((y_i_pred[n_i:2*n_i] - y_i[2*n_i:3*n_i]) ** 2)
    mse_dr_i = np.mean((y_i_pred[2*n_i:3*n_i] - y_i[2*n_i:3*n_i]) ** 2)
    print(f"  {boat_names[i]}: du={mse_du_i:.6f}, dv={mse_dv_i:.6f}, dr={mse_dr_i:.6f}, total={mse_du_i+mse_dv_i+mse_dr_i:.6f}")

# ========================================
# 15. Dedicated: USV1+USV3 pooling → identify → validate on USV2
# ========================================
print("\n" + "=" * 60)
print("Dedicated: Train on USV1+USV3, Validate on USV2")
print("=" * 60)

# Pool USV1(0) + USV3(2)
train_cv_idx = [0, 2]
test_cv_idx = 1
X_train_cv = np.vstack([X_list[j] for j in train_cv_idx])
y_train_cv = np.concatenate([y_list[j] for j in train_cv_idx])

result_cv = minimize(
    loss_regression, initial_params,
    args=(X_train_cv, y_train_cv),
    method='SLSQP', bounds=opt_bounds,
    options={'disp': True, 'maxiter': 2000}
)

if result_cv.success:
    theta_cv = result_cv.x
    print("\nOptimization converged!")
    print(f"Final loss: {result_cv.fun:.6f}")
else:
    print("\nOptimization failed: " + result_cv.message)
    theta_cv = result_cv.x

# Print identified model from USV1+USV3
a_cv = theta_cv[0:7]
b_cv = theta_cv[7:14]
c_cv = theta_cv[14:21]
print("\n--- Identified Model from USV1+USV3 Pooling ---")
print(f"du = {a_cv[0]:.6f}*v*r + {a_cv[1]:.6f}*u + {a_cv[2]:.6f}*v + {a_cv[3]:.6f}*r + {a_cv[4]:.6f}*Tp + {a_cv[5]:.6f}*Ts + {a_cv[6]:.6f}")
print(f"dv = {b_cv[0]:.6f}*u*r + {b_cv[1]:.6f}*u + {b_cv[2]:.6f}*v + {b_cv[3]:.6f}*r + {b_cv[4]:.6f}*Tp + {b_cv[5]:.6f}*Ts + {b_cv[6]:.6f}")
print(f"dr = {c_cv[0]:.6f}*u*v + {c_cv[1]:.6f}*u + {c_cv[2]:.6f}*v + {c_cv[3]:.6f}*r + {c_cv[4]:.6f}*Tp + {c_cv[5]:.6f}*Ts + {c_cv[6]:.6f}")

# Validation errors on training boats (self-prediction)
print("\n--- Self-prediction on Training Boats (normalized space) ---")
for j in train_cv_idx:
    Xj = X_list[j]
    yj = y_list[j]
    yj_pred = Xj @ theta_cv
    nj = n_list[j]
    mse_du = np.mean((yj_pred[0:nj] - yj[0:nj]) ** 2)
    mse_dv = np.mean((yj_pred[nj:2*nj] - yj[2*nj:3*nj]) ** 2)
    mse_dr = np.mean((yj_pred[2*nj:3*nj] - yj[2*nj:3*nj]) ** 2)
    print(f"  {boat_names[j]}: du={mse_du:.6f}, dv={mse_dv:.6f}, dr={mse_dr:.6f}")

# Cross-prediction on USV2
print("\n--- Cross-validation on USV2 (test boat) ---")
X_test = X_list[test_cv_idx]
y_test = y_list[test_cv_idx]
y_test_pred = X_test @ theta_cv
n_test = n_list[test_cv_idx]
mse_du_test = np.mean((y_test_pred[0:n_test] - y_test[0:n_test]) ** 2)
mse_dv_test = np.mean((y_test_pred[n_test:2*n_test] - y_test[2*n_test:3*n_test]) ** 2)
mse_dr_test = np.mean((y_test_pred[2*n_test:3*n_test] - y_test[2*n_test:3*n_test]) ** 2)
print(f"  USV2: du={mse_du_test:.6f}, dv={mse_dv_test:.6f}, dr={mse_dr_test:.6f}, total={mse_du_test+mse_dv_test+mse_dr_test:.6f}")

# Trajectory simulation on USV2 using the USV1+USV3 model
print("\n--- Trajectory Simulation on USV2 (using USV1+USV3 model) ---")
raw_test = raw_data[test_cv_idx]
n_sim_test = raw_test['N']
x0, y0, psi0 = raw_test['x'][0], raw_test['y'][0], raw_test['psi'][0]

x_sim_cv, y_sim_cv, psi_sim_cv, u_sim_cv, v_sim_cv, r_sim_cv = simulate_with_params(
    theta_cv, raw_test, norm_data[test_cv_idx]['scaler'], x0, y0, psi0, dt, n_sim_test
)

time_test = np.arange(n_sim_test) * dt
traj_err_cv = np.sqrt((x_sim_cv - raw_test['x']) ** 2 + (y_sim_cv - raw_test['y']) ** 2)
print(f"  USV2 Mean trajectory error: {np.mean(traj_err_cv):.4f}m")
print(f"  USV2 Max trajectory error:  {np.max(traj_err_cv):.4f}m")

# Detailed state prediction comparison
print("\n--- State Variable RMSE on USV2 ---")
rmse_u = np.sqrt(np.mean((u_sim_cv - raw_test['u']) ** 2))
rmse_v = np.sqrt(np.mean((v_sim_cv - raw_test['v']) ** 2))
rmse_r = np.sqrt(np.mean((r_sim_cv - raw_test['r']) ** 2))
print(f"  u: RMSE = {rmse_u:.4f} m/s")
print(f"  v: RMSE = {rmse_v:.4f} m/s")
print(f"  r: RMSE = {rmse_r:.4f} rad/s")


# ========================================
# 16. Figure A: USV1~3 trajectory display
# ========================================
print("\n--- Figure A: USV1~3 trajectory display ---")
fig_A, ax_A = plt.subplots(figsize=(7, 5))
colors = ['C0', 'C1', 'C2']
for i in range(n_boats):
    raw = raw_data[i]
    x0, y0, psi0 = raw['x'][0], raw['y'][0], raw['psi'][0]
    x_sim, y_sim, _, _, _, _ = simulate_with_params(
        theta_pool, raw, norm_data[i]['scaler'], x0, y0, psi0, dt, raw['N']
    )
    ax_A.plot(raw['x'], raw['y'], color=colors[i], linestyle='-',
              label=f'{boat_names[i]} Measured', linewidth=1.5)
    ax_A.plot(x_sim, y_sim, color=colors[i], linestyle='--',
              label=f'{boat_names[i]} Simulated', linewidth=1.5)
ax_A.set_xlabel('x (m)'); ax_A.set_ylabel('y (m)')
ax_A.legend(fontsize=7); ax_A.axis('equal')
fig_A.tight_layout()

# ========================================
# 17. Figure B: 4x1 plot of u, v, r, psi for all 3 USVs
# ========================================
print("\n--- Figure B: u, v, r, psi comparison for all 3 USVs ---")
fig_B, axes_B = plt.subplots(4, 1, figsize=(8, 10))
colors = ['C0', 'C1', 'C2']

for i in range(n_boats):
    raw = raw_data[i]
    n_sim = raw['N']
    x0, y0, psi0 = raw['x'][0], raw['y'][0], raw['psi'][0]
    x_sim, y_sim, psi_sim, u_sim, v_sim, r_sim = simulate_with_params(
        theta_pool, raw, norm_data[i]['scaler'], x0, y0, psi0, dt, n_sim
    )
    time = np.arange(n_sim) * dt
    
    axes_B[0].plot(time, raw['u'], color=colors[i], linestyle='-', label=f'{boat_names[i]} Measured', linewidth=1.2)
    axes_B[0].plot(time, u_sim, color=colors[i], linestyle='--', label=f'{boat_names[i]} Simulated', linewidth=1.2)
    
    axes_B[1].plot(time, raw['v'], color=colors[i], linestyle='-', label=f'{boat_names[i]} Measured', linewidth=1.2)
    axes_B[1].plot(time, v_sim, color=colors[i], linestyle='--', label=f'{boat_names[i]} Simulated', linewidth=1.2)
    
    axes_B[2].plot(time, raw['r'], color=colors[i], linestyle='-', label=f'{boat_names[i]} Measured', linewidth=1.2)
    axes_B[2].plot(time, r_sim, color=colors[i], linestyle='--', label=f'{boat_names[i]} Simulated', linewidth=1.2)
    
    axes_B[3].plot(time, np.unwrap(raw['psi']), color=colors[i], linestyle='-', label=f'{boat_names[i]} Measured', linewidth=1.2)
    axes_B[3].plot(time, np.unwrap(psi_sim), color=colors[i], linestyle='--', label=f'{boat_names[i]} Simulated', linewidth=1.2)

axes_B[0].set_ylabel('u (m/s)')
axes_B[1].set_ylabel('v (m/s)')
axes_B[2].set_ylabel('r (rad/s)')
axes_B[3].set_xlabel('Time (s)'); axes_B[3].set_ylabel('psi (rad)')
axes_B[0].legend(fontsize=6); 
fig_B.tight_layout()

# ========================================
# 18. Figure C: Original trajectories (with labels, sparser ticks)
# ========================================
print("\n--- Figure C: Original 3 USV trajectories ---")
fig_C, ax_C = plt.subplots(figsize=(7, 5))
colors_C = ['C0', 'C1', 'C2']
for i in range(n_boats):
    ax_C.plot(raw_data[i]['x'], raw_data[i]['y'], color=colors_C[i], linestyle='-',
              label=boat_names[i], linewidth=2)
ax_C.set_xlabel('x (m)', fontsize=9); ax_C.set_ylabel('y (m)', fontsize=9)
ax_C.legend(fontsize=8); ax_C.axis('equal')
ax_C.xaxis.set_major_locator(MaxNLocator(4))
ax_C.yaxis.set_major_locator(MaxNLocator(4))
fig_C.tight_layout()

# ========================================
# 19. Figure D: Measured + Simulated overlay (with labels, sparser ticks)
# ========================================
print("\n--- Figure D: Measured + Simulated overlay (all 3 USVs, pooled model) ---")
fig_D, ax_D = plt.subplots(figsize=(7, 5))
colors_D = ['C0', 'C1', 'C2']
for i in range(n_boats):
    raw = raw_data[i]
    x0, y0, psi0 = raw['x'][0], raw['y'][0], raw['psi'][0]
    x_sim, y_sim, _, _, _, _ = simulate_with_params(
        theta_pool, raw, norm_data[i]['scaler'], x0, y0, psi0, dt, raw['N']
    )
    ax_D.plot(raw['x'], raw['y'], color=colors_D[i], linestyle='-',
              label=f'{boat_names[i]} Measured', linewidth=1.5)
    ax_D.plot(x_sim, y_sim, color=colors_D[i], linestyle='--',
              label=f'{boat_names[i]} Simulated', linewidth=2)
ax_D.set_xlabel('x (m)', fontsize=9); ax_D.set_ylabel('y (m)', fontsize=9)
ax_D.legend(fontsize=7); ax_D.axis('equal')
ax_D.xaxis.set_major_locator(MaxNLocator(4))
ax_D.yaxis.set_major_locator(MaxNLocator(4))
fig_D.tight_layout()

# ========================================
# 20. Figure E: Heatmap of the unified 21-parameter model (vertical)
# ========================================
print("\n--- Figure E: Parameter heatmap (vertical) ---")
theta_display = theta_pool.copy()
fig_E, ax_E = plt.subplots(figsize=(5, 7))

matrix = np.zeros((7, 3))
for j in range(3):
    for i in range(7):
        matrix[i, j] = theta_display[j * 7 + i]

mask = np.isnan(matrix)
colors_hm = [(0.9, 0.2, 0.2), (1, 1, 1), (0.2, 0.6, 0.9)]
cmap_hm = LinearSegmentedColormap.from_list('custom_cmap', colors_hm, N=256)

param_names = ['v*r', 'u', 'v', 'r', 'Tp', 'Ts', '1']
state_labels = ['$\\dot{u}$', '$\\dot{v}$', '$\\dot{r}$']
annotations = np.empty((7, 3), dtype=object)
for j in range(3):
    for i in range(7):
        val = theta_display[j * 7 + i]
        if abs(val) >= 10:
            fmt_val = f"{val:.3f}"
        elif abs(val) >= 0.1:
            fmt_val = f"{val:.4f}"
        else:
            fmt_val = f"{val:.5f}"
        annotations[i, j] = f"{fmt_val}"

sns.heatmap(matrix, ax=ax_E, mask=mask, annot=annotations, fmt='',
            annot_kws={'fontsize': 10}, cmap=cmap_hm,
            cbar_kws={'label': 'Parameter Value'},
            xticklabels=state_labels,
            yticklabels=[f'$\\theta_{{{i+1}}}$\n({param_names[i]})' for i in range(7)],
            linewidths=0.5, linecolor='#e6e6e6')
ax_E.set_title('Identified Unified Model\n(21-parameter)', fontsize=12, fontweight='bold')
ax_E.set_xticklabels(state_labels, fontsize=10)
ax_E.set_yticklabels([f'$\\theta_{{{i+1}}}$\n({param_names[i]})' for i in range(7)], rotation=0, fontsize=9)
fig_E.tight_layout()

# ========================================
# 21. Figure F: Training signals (u, v, r, Tp, Ts) — first 100 rows, xy swapped, side-by-side
# ========================================
print("\n--- Figure F: Training signals (u/v/r/Tp/Ts, xy swapped, side-by-side) ---")
N_plot = 100
fig_F, axes_F = plt.subplots(1, 5, figsize=(10, 3.5))
signal_names = ['u', 'v', 'r', 'Tp', 'Ts']
colors_F = {'USV1': '#1f77b4', 'USV3': '#d62728'}
time_F = np.arange(N_plot) * dt

for j, sig in enumerate(signal_names):
    for idx in train_cv_idx:
        tag = boat_names[idx]
        axes_F[j].plot(raw_data[idx][sig][:N_plot], time_F,
                       color=colors_F[tag], linewidth=2.5)
    axes_F[j].set_xticks([])
    axes_F[j].set_yticks([])
    axes_F[j].invert_yaxis()
fig_F.tight_layout(pad=0.5)

# ========================================
# 22. Figure G: Training derivatives (du, dv, dr) — first 100 rows, xy swapped, side-by-side
# ========================================
print("\n--- Figure G: Training derivatives (du/dv/dr, xy swapped, side-by-side) ---")
fig_G, axes_G = plt.subplots(1, 3, figsize=(6, 3.5))
deriv_names = ['du', 'dv', 'dr']
colors_G = {'USV1': '#1f77b4', 'USV3': '#d62728'}

for j, sig in enumerate(deriv_names):
    for idx in train_cv_idx:
        tag = boat_names[idx]
        axes_G[j].plot(raw_data[idx][sig][:N_plot], time_F,
                       color=colors_G[tag], linewidth=2.5)
    axes_G[j].set_xticks([])
    axes_G[j].set_yticks([])
    axes_G[j].invert_yaxis()
fig_G.tight_layout(pad=0.5)

plt.show()

print("\n=== Multi-USV Model Identification Complete ===")
print(f"Pooled model parameters saved. Cross-validation finished.")

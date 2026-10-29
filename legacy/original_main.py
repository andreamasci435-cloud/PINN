import torch
import torch.nn as nn
import numpy as np
import matplotlib.pyplot as plt

# Reproducibility
torch.manual_seed(42)
np.random.seed(42)

# ==========================================
# 1. PARAMETRI FISSI E GENERAZIONE DATI
# ==========================================
L = 0.5  # Lunghezza barra (m)
t_max = 200.0  # Tempo totale (s)
T_amb = 20.0  # Temperatura ambiente (°C)

# Parametri presi come noti (costanti)
ALPHA_FIXED = 1e-4  # Diffusività termica (m^2/s)
BETA_FIXED = 0.01  # Dissipazione convettiva (1/s)

# Simulazione a differenze finite (Ground Truth)
Nx_sim = 50
dt_sim = 0.1
Nt_sim = int(t_max / dt_sim) + 1

dx_sim = L / (Nx_sim - 1)
x_grid = np.linspace(0, L, Nx_sim)
t_grid = np.linspace(0, t_max, Nt_sim)

T_matrix = np.zeros((Nt_sim, Nx_sim)) + T_amb
T_matrix[:, 0] = 80.0  # Estremità riscaldata a 80°C

for n in range(0, Nt_sim - 1):
    d2T = (T_matrix[n, 2:] - 2 * T_matrix[n, 1:-1] + T_matrix[n, :-2]) / (dx_sim ** 2)
    T_matrix[n + 1, 1:-1] = T_matrix[n, 1:-1] + dt_sim * (ALPHA_FIXED * d2T - BETA_FIXED * (T_matrix[n, 1:-1] - T_amb))
    T_matrix[n + 1, -1] = T_matrix[n + 1, -2]  # Isolamento a destra

# Campionamento degli 8 sensori fisici
sensor_indices = np.linspace(2, Nx_sim - 3, 8, dtype=int)
time_indices = np.arange(0, Nt_sim, int(2.0 / dt_sim))

X_data_list, T_data_list = [], []
for s_idx in sensor_indices:
    for t_idx in time_indices:
        X_data_list.append([x_grid[s_idx], t_grid[t_idx]])
        # Rumore reale di misura
        T_data_list.append([T_matrix[t_idx, s_idx] + np.random.normal(0, 0.15)])

# Punti al contorno x=0 (80°C)
for t_val in np.linspace(0, t_max, 100):
    X_data_list.append([0.0, t_val])
    T_data_list.append([80.0])

X_data = torch.tensor(X_data_list, dtype=torch.float32)
T_data = torch.tensor(T_data_list, dtype=torch.float32)

# Punti di collocazione per far rispettare la PDE nel continuo
N_phys = 3000
x_phys = torch.rand(N_phys, 1) * L
t_phys = torch.rand(N_phys, 1) * t_max
X_phys = torch.cat([x_phys, t_phys], dim=1)


# ==========================================
# 2. ARCHITETTURA PINN
# ==========================================
class ForwardPINN(nn.Module):
    def __init__(self):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(2, 40),
            nn.Tanh(),
            nn.Linear(40, 40),
            nn.Tanh(),
            nn.Linear(40, 40),
            nn.Tanh(),
            nn.Linear(40, 1)
        )

    def forward(self, x, t):
        x_norm = 2.0 * (x / L) - 1.0
        t_norm = 2.0 * (t / t_max) - 1.0
        inputs = torch.cat([x_norm, t_norm], dim=1)
        return self.net(inputs)


def pde_residual(model, x, t):
    x.requires_grad_(True)
    t.requires_grad_(True)

    T = model(x, t)
    dT_dt = torch.autograd.grad(T, t, torch.ones_like(T), create_graph=True)[0]
    dT_dx = torch.autograd.grad(T, x, torch.ones_like(T), create_graph=True)[0]
    d2T_dx2 = torch.autograd.grad(dT_dx, x, torch.ones_like(dT_dx), create_graph=True)[0]

    residual = dT_dt - ALPHA_FIXED * d2T_dx2 + BETA_FIXED * (T - T_amb)
    return residual


# ==========================================
# 3. ADDESTRAMENTO PROLUNGATO CON SCHEDULER
# ==========================================
model = ForwardPINN()
optimizer = torch.optim.Adam(model.parameters(), lr=1e-3)
scheduler = torch.optim.lr_scheduler.StepLR(optimizer, step_size=4000, gamma=0.5)

epochs = 18000
print(f"--- Inizio Addestramento Avanzato ({epochs} epoche) ---")

for epoch in range(1, epochs + 1):
    optimizer.zero_grad()

    # Loss sui dati misurati dai sensori
    T_pred = model(X_data[:, 0:1], X_data[:, 1:2])
    loss_data = torch.mean((T_pred - T_data) ** 2)

    # Loss sul residuo dell'equazione differenziale
    res = pde_residual(model, X_phys[:, 0:1], X_phys[:, 1:2])
    loss_phys = torch.mean(res ** 2)

    # Loss Totale pesata
    loss = loss_data + 1e-2 * loss_phys
    loss.backward()
    optimizer.step()
    scheduler.step()

    if epoch % 2000 == 0:
        current_lr = optimizer.param_groups[0]['lr']
        print(f"Epoch {epoch:5d}/{epochs} | Loss Data: {loss_data.item():.5f} | "
              f"Loss Phys: {loss_phys.item():.5f} | LR: {current_lr:.6f}")

# ==========================================
# 4. GRAFICO DEI RISULTATI
# ==========================================
fig, ax = plt.subplots(figsize=(11, 6))

t_test_times = [10.0, 30.0, 80.0, 200.0]

for t_val in t_test_times:
    t_idx = int(t_val / dt_sim)

    # Curva teorica reale
    ax.plot(x_grid, T_matrix[t_idx, :], '--', label=f'Dati Reali (t={t_val}s)')

    # Curva continua stimata dalla PINN
    x_test = torch.tensor(x_grid, dtype=torch.float32).view(-1, 1)
    t_test = torch.tensor(np.full_like(x_grid, t_val), dtype=torch.float32).view(-1, 1)

    with torch.no_grad():
        T_pinn = model(x_test, t_test).numpy()

    ax.plot(x_grid, T_pinn, '-', linewidth=2, label=f'PINN Predizione (t={t_val}s)')

# Posizione degli 8 sensori fisici lungo la barra
sensor_x = x_grid[sensor_indices]
ax.scatter(sensor_x, [20] * len(sensor_x), color='red', zorder=5, marker='^', s=90, label='Posizione 8 Sensori')

ax.set_xlabel('Posizione lungo la barra x [m]')
ax.set_ylabel('Temperatura T [°C]')
ax.set_title('Ricostruzione della Temperatura $T(x,t)$ con PINN (Alpha e Beta fissi)')
ax.legend()
ax.grid(True)

plt.tight_layout()
plt.show()
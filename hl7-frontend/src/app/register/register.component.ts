import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Router } from '@angular/router';
import { HttpClient } from '@angular/common/http';

@Component({
  selector: 'app-register',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './register.component.html',
  styleUrls: ['./register.component.scss']
})
export class RegisterComponent {
  username = '';
  password = '';
  function = '';
  role = 'Utilisateur';

  constructor(private http: HttpClient, private router: Router) {}
  goToHome() {
    window.location.href = '/';
  }
  showPassword: boolean = false;

  togglePasswordVisibility(): void {
    this.showPassword = !this.showPassword;
  }
    
  onSubmit(): void {
    if (!this.username || !this.password || !this.function || !this.role) {
      alert('⚠️ Tous les champs sont requis.');
      return;
    }
    const passwordRegex = /^(?=.*[A-Z])(?=.*[!@#$%^&*])[A-Za-z\d!@#$%^&*]{8,}$/;
    if (!passwordRegex.test(this.password)) {
      alert("❌ Le mot de passe doit contenir au moins 8 caractères, une majuscule et un caractère spécial.");
      return;
    }
    const userData = {
      username: this.username,
      password: this.password,
      function: this.function,
      role: this.role
    };
  
    this.http.post('http://localhost:8000/register', userData).subscribe({
      next: () => {
        alert('✅ Compte créé avec succès ! Redirection vers la connexion...');
        this.router.navigate(['/login']);  // ✅ Redirection ici
      },
      error: (err) => {
        alert('❌ Une erreur est survenue lors de l’inscription.');
        console.error(err);
      }
    });
  }
}

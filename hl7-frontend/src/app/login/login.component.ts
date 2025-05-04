import { Component } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { Router } from '@angular/router';
import { CommonModule } from '@angular/common';
import { HttpClientModule } from '@angular/common/http';

import { AuthService } from '../services/auth.service';

@Component({
  selector: 'app-login',
  standalone: true, // ✅ OBLIGATOIRE avec loadComponent()
  imports: [CommonModule, FormsModule, HttpClientModule], // ✅ nécessaire pour ngModel et http
  templateUrl: './login.component.html',
  styleUrls: ['./login.component.scss']
})
export class LoginComponent {
  username: string = '';
  password: string = '';

  constructor(private auth: AuthService, private router: Router) {}
  showPassword: boolean = false;

 togglePasswordVisibility(): void {
  this.showPassword = !this.showPassword;
 }
  // ✅ Soumission du formulaire de connexion
  onSubmit(): void {
    this.auth.login({ username: this.username, password: this.password }).subscribe({
      next: (res) => {
        console.log('✅ Connexion réussie', res);
        this.router.navigate(['/messages']);
      },
      error: (err) => {
        alert('❌ Identifiants incorrects');
        console.error(err);
      }
    });
  }

  // ✅ Redirection vers inscription
  goToRegister(): void {
    this.router.navigate(['/register']);
  }
}
